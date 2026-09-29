"""Invoice CRUD + CSV export + PDF download + send-email routes."""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import compute_totals, csv_response, send_pdf_email
from erp_models import EmailSendRequest, Invoice, InvoiceIn, Party
from erp_pdf import render_invoice_pdf, render_deposit_receipt_pdf


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:
    @router.get("/invoices", response_model=List[Invoice])
    async def list_invoices(_: dict = Depends(auth_dep)):
        cur = db.erp_invoices.find({}, {"_id": 0}).sort("number", -1)
        return [Invoice(**d) async for d in cur]

    @router.get("/invoices/deposits")
    async def list_deposits(_: dict = Depends(auth_dep)):
        """Factures avec dépôt reçu — solde restant à encaisser."""
        cur = db.erp_invoices.find(
            {"deposit_received": True, "status": {"$ne": "annulée"}}, {"_id": 0}
        ).sort("number", -1)
        rows, total_dep, total_bal = [], 0.0, 0.0
        async for i in cur:
            paid = i.get("status") == "payée"
            dep = float(i.get("deposit_amount") or 0)
            bal_raw = i.get("balance_due")
            bal = float(bal_raw) if bal_raw is not None else round(float(i.get("total") or 0) - dep, 2)
            remaining = 0.0 if paid else bal
            cs = i.get("customer_snapshot") or {}
            rows.append({
                "id": i.get("id"),
                "number": i.get("number"),
                "date": i.get("date"),
                "customer_name": cs.get("name") or "—",
                "total": float(i.get("total") or 0),
                "deposit_pct": float(i.get("deposit_pct") or 0),
                "deposit_amount": dep,
                "balance_due": bal,
                "remaining": remaining,
                "status": i.get("status") or "",
            })
            total_dep += dep
            total_bal += remaining

        # Dépôts ATTENDUS : soumissions acceptées avec dépôt annoncé, pas encore reçu
        awaited, total_awaited = [], 0.0
        qcur = db.erp_quotes.find(
            {"status": "acceptée", "show_deposit": True}, {"_id": 0}
        ).sort("number", -1)
        async for q in qcur:
            pct = float(q.get("deposit_pct") or 0)
            if pct <= 0:
                continue
            # Déjà reçu ? (facture liée avec dépôt encaissé)
            inv_id = q.get("converted_invoice_id")
            if inv_id:
                linked = await db.erp_invoices.find_one({"id": inv_id}, {"_id": 0, "deposit_received": 1})
                if linked and linked.get("deposit_received"):
                    continue
            total = float(q.get("total") or 0)
            expected = round(total * pct / 100, 2)
            cs = q.get("customer_snapshot") or {}
            awaited.append({
                "id": q.get("id"),
                "number": q.get("number"),
                "date": q.get("date"),
                "customer_name": cs.get("name") or "—",
                "total": total,
                "deposit_pct": pct,
                "expected_deposit": expected,
                "converted": bool(inv_id),
            })
            total_awaited += expected

        return {"invoices": rows,
                "total_deposit": round(total_dep, 2),
                "total_remaining": round(total_bal, 2),
                "awaited": awaited,
                "total_awaited": round(total_awaited, 2)}

    @router.post("/invoices", response_model=Invoice, status_code=201)
    async def create_invoice(data: InvoiceIn, _: dict = Depends(auth_dep)):
        number = await next_number("invoice")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        dep_pct = float(data.deposit_pct or 0) if data.deposit_received else 0.0
        dep_amount = round(total * dep_pct / 100, 2) if data.deposit_received else 0.0
        balance = round(total - dep_amount, 2)
        inv = Invoice(
            number=number,
            customer_id=data.customer_id,
            customer_snapshot=Party(**data.customer_snapshot.model_dump()),
            date=data.date,
            due_date=data.due_date,
            items=data.items,
            subtotal=subtotal, tps=tps, tvq=tvq, total=total,
            taxable=data.taxable, notes=data.notes, status=data.status,
            deposit_received=data.deposit_received, deposit_pct=dep_pct,
            deposit_amount=dep_amount, balance_due=balance,
        )
        await db.erp_invoices.insert_one(inv.model_dump())
        return inv

    @router.get("/invoices/{invoice_id}", response_model=Invoice)
    async def get_invoice(invoice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        return Invoice(**doc)

    @router.put("/invoices/{invoice_id}", response_model=Invoice)
    async def update_invoice(invoice_id: str, data: InvoiceIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Facture introuvable")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        dep_pct = float(data.deposit_pct or 0) if data.deposit_received else 0.0
        dep_amount = round(total * dep_pct / 100, 2) if data.deposit_received else 0.0
        balance = round(total - dep_amount, 2)
        update_fields = {
            "customer_id": data.customer_id,
            "customer_snapshot": Party(**data.customer_snapshot.model_dump()).model_dump(),
            "date": data.date,
            "due_date": data.due_date,
            "items": [it.model_dump() for it in data.items],
            "subtotal": subtotal, "tps": tps, "tvq": tvq, "total": total,
            "taxable": data.taxable, "notes": data.notes, "status": data.status,
            "deposit_received": data.deposit_received, "deposit_pct": dep_pct,
            "deposit_amount": dep_amount, "balance_due": balance,
        }
        await db.erp_invoices.update_one({"id": invoice_id}, {"$set": update_fields})
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        return Invoice(**doc)

    @router.delete("/invoices/{invoice_id}")
    async def delete_invoice(invoice_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_invoices.delete_one({"id": invoice_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Facture introuvable")
        return {"deleted": invoice_id}

    @router.post("/invoices/{invoice_id}/mark-paid", response_model=Invoice)
    async def mark_invoice_paid(invoice_id: str, _: dict = Depends(auth_dep)):
        """One-click status change: brouillon|envoyée → payée. Stops the
        automatic reminder cycle. No-op if already paid/cancelled."""
        existing = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Facture introuvable")
        if existing.get("status") == "payée":
            return Invoice(**existing)
        if existing.get("status") == "annulée":
            raise HTTPException(400, "Facture annulée — impossible de marquer payée")
        await db.erp_invoices.update_one(
            {"id": invoice_id},
            {"$set": {"status": "payée"}},
        )
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        return Invoice(**doc)

    @router.get("/invoices/{invoice_id}/deposit-receipt.pdf")
    async def deposit_receipt_pdf(invoice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        if not doc.get("deposit_received"):
            raise HTTPException(400, "Aucun dépôt reçu sur cette facture.")
        pdf_bytes = await asyncio.to_thread(render_deposit_receipt_pdf, doc)
        filename = f"recu-depot-FAC-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    @router.post("/invoices/{invoice_id}/deposit-receipt/send")
    async def send_deposit_receipt(invoice_id: str, body: dict | None = None,
                                   _: dict = Depends(auth_dep)):
        """Email the deposit receipt PDF to the client (defaults to the
        customer's email on the invoice)."""
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        if not doc.get("deposit_received"):
            raise HTTPException(400, "Aucun dépôt reçu sur cette facture.")
        cs = doc.get("customer_snapshot") or {}
        to_email = ((body or {}).get("to_email") or cs.get("email") or "").strip()
        if not to_email:
            raise HTTPException(400, "Aucun courriel client. Entrez une adresse.")
        num = f"FAC-{int(doc['number']):04d}"
        dep = float(doc.get("deposit_amount") or 0)
        bal = doc.get("balance_due")
        bal = float(bal) if bal is not None else round(float(doc.get("total") or 0) - dep, 2)
        pdf_bytes = await asyncio.to_thread(render_deposit_receipt_pdf, doc)
        html = (
            f"<p>Bonjour,</p>"
            f"<p>Nous confirmons la réception de votre dépôt de <b>{dep:,.2f} $</b> "
            f"en lien avec la facture <b>{num}</b>.</p>"
            f"<p>Solde restant à payer : <b>{bal:,.2f} $</b>.</p>"
            f"<p>Le reçu officiel est en pièce jointe. Merci de votre confiance !</p>"
        )
        await send_pdf_email(
            to_email=to_email,
            subject=f"Reçu de dépôt — {num} — Portech",
            html=html, pdf_bytes=pdf_bytes,
            filename=f"recu-depot-{num}.pdf",
        )
        return {"sent": True, "to_email": to_email}

    @router.post("/invoices/{invoice_id}/bill-balance", response_model=Invoice)
    async def bill_balance(invoice_id: str, _: dict = Depends(auth_dep)):
        """Create the FINAL invoice for the remaining balance after a deposit.

        The balance invoice is NON-taxable (a single line at the exact remaining
        amount) because the taxes were already declared on the original invoice —
        this avoids any double taxation. The original invoice is marked 'payée'
        (deposit collected, balance now billed separately)."""
        orig = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not orig:
            raise HTTPException(404, "Facture introuvable")
        if not orig.get("deposit_received"):
            raise HTTPException(400, "Cette facture n'a pas de dépôt reçu.")
        if orig.get("status") in ("payée", "annulée"):
            raise HTTPException(400, "Facture déjà payée ou annulée.")
        dep = float(orig.get("deposit_amount") or 0)
        bal = orig.get("balance_due")
        bal = float(bal) if bal is not None else round(float(orig.get("total") or 0) - dep, 2)
        if bal <= 0:
            raise HTTPException(400, "Aucun solde restant à facturer.")
        orig_num = f"FAC-{int(orig['number']):04d}"
        pct = float(orig.get("deposit_pct") or 0)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        number = await next_number("invoice")
        line = {
            "description": f"Solde final — réf. {orig_num} (après dépôt de {pct:g} %, taxes déjà facturées)",
            "quantity": 1, "unit_price": bal, "product_id": None,
        }
        inv = Invoice(
            number=number,
            customer_id=orig.get("customer_id"),
            customer_snapshot=Party(**(orig.get("customer_snapshot") or {})),
            date=today,
            items=[line],
            subtotal=bal, tps=0.0, tvq=0.0, total=bal,
            taxable=False,
            notes=f"Facture de solde suite au dépôt reçu sur {orig_num}.",
            status="envoyée",
        )
        await db.erp_invoices.insert_one(inv.model_dump())
        await db.erp_invoices.update_one({"id": invoice_id}, {"$set": {"status": "payée"}})
        return inv

    @router.get("/exports/invoices.csv")
    async def export_invoices(_: dict = Depends(auth_dep)):
        invoices = await db.erp_invoices.find({}, {"_id": 0}).sort("number", -1).to_list(length=None)
        rows = []
        for i in invoices:
            cs = i.get("customer_snapshot") or {}
            rows.append({
                "Numéro": f"FAC-{int(i.get('number', 0)):04d}",
                "Date": i.get("date"),
                "Échéance": i.get("due_date") or "",
                "Client": cs.get("name") or "",
                "Ville": cs.get("city") or "",
                "Courriel": cs.get("email") or "",
                "Sous-total": f"{i.get('subtotal', 0):.2f}",
                "TPS": f"{i.get('tps', 0):.2f}",
                "TVQ": f"{i.get('tvq', 0):.2f}",
                "Total": f"{i.get('total', 0):.2f}",
                "Statut": i.get("status") or "",
                "Notes": (i.get("notes") or "").replace("\n", " "),
            })
        return csv_response(rows, "factures-portech.csv")

    @router.get("/invoices/{invoice_id}/pdf")
    async def download_invoice_pdf(invoice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        pdf_bytes = await asyncio.to_thread(render_invoice_pdf, doc)
        filename = f"FAC-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    @router.post("/invoices/{invoice_id}/send-email")
    async def send_invoice_email(invoice_id: str, payload: EmailSendRequest, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        pdf_bytes = await asyncio.to_thread(render_invoice_pdf, doc)
        number = f"FAC-{int(doc['number']):04d}"
        cust = (doc.get("customer_snapshot") or {}).get("name") or ""
        subject = payload.subject or f"Portech — Facture {number}"
        message_html = payload.message or (
            f"<p>Bonjour {cust},</p>"
            f"<p>Vous trouverez en pièce jointe votre facture <b>{number}</b> "
            f"d'un total de <b>{doc.get('total', 0):.2f} $ CAD</b>.</p>"
            "<p>Modalités : paiement net 30 jours.<br/>"
            "Pour toute question, répondez simplement à ce courriel.</p>"
        )
        await send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
            footer_note=f"Facture {number} · Portech ERP",
        )
        if doc.get("status") == "brouillon":
            await db.erp_invoices.update_one(
                {"id": invoice_id}, {"$set": {"status": "envoyée"}},
            )
        return {"sent": True, "to": payload.to_email}
