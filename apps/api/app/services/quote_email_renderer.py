from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.lead import Lead
from app.models.restaurant import Restaurant


class QuoteEmailRenderer:
    def render(
        self,
        quote: Quote,
        items: list[QuoteItem],
        lead: Lead,
        restaurant: Restaurant | None = None,
    ) -> tuple[str, str]:
        restaurant_name = restaurant.name if restaurant else "Catering Services"
        contact_info = f"{restaurant.phone or ''}" if restaurant else ""

        lead_name = lead.contact_name if lead and lead.contact_name else "Valued Client"
        company = f"({lead.company_name})" if lead and lead.company_name else ""
        lead_email = lead.email if lead else ""

        event_date_str = str(quote.event_date) if quote.event_date else "N/A"
        event_type_str = quote.event_type or "Catering Event"
        valid_until_str = str(quote.valid_until) if quote.valid_until else "N/A"

        # Build items table HTML & text
        item_rows_html = []
        item_rows_text = []

        for idx, item in enumerate(items, 1):
            desc = f"<br><small style='color: #666;'>{item.description}</small>" if item.description else ""
            item_rows_html.append(
                f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{idx}. {item.name}{desc}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${item.unit_price:.2f}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">${item.total:.2f}</td>
                </tr>
                """
            )
            item_rows_text.append(
                f"- {item.name} x{item.quantity} @ ${item.unit_price:.2f} = ${item.total:.2f}"
            )

        items_html = "\n".join(item_rows_html)
        items_text = "\n".join(item_rows_text)

        tax_pct = float(quote.tax_rate or 0) * 100
        tax_pct_str = f"{tax_pct:.1f}%"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                .container {{ max-width: 650px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
                .header {{ background-color: #1a202c; color: white; padding: 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 24px; }}
                .details-box {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th {{ background-color: #f1f5f9; padding: 10px; text-align: left; font-weight: 600; }}
                .totals {{ width: 250px; margin-left: auto; text-align: right; margin-bottom: 20px; }}
                .totals td {{ padding: 6px 0; }}
                .grand-total {{ font-size: 18px; font-weight: bold; color: #16a34a; border-top: 2px solid #333; }}
                .footer {{ background-color: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #64748b; }}
                .terms {{ font-size: 12px; color: #475569; background: #fffbe6; border: 1px solid #ffe58f; padding: 12px; border-radius: 4px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{restaurant_name}</h1>
                    <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.8;">{contact_info}</p>
                </div>
                <div class="content">
                    <h2>Catering Quote #{quote.quote_number}</h2>
                    <div class="details-box">
                        <p style="margin: 0 0 8px 0;"><strong>Prepared For:</strong> {lead_name} {company} ({lead_email})</p>
                        <p style="margin: 0 0 8px 0;"><strong>Event Type:</strong> {event_type_str}</p>
                        <p style="margin: 0 0 8px 0;"><strong>Event Date:</strong> {event_date_str}</p>
                        <p style="margin: 0 0 8px 0;"><strong>Guest Count:</strong> {quote.guest_count} guests</p>
                        <p style="margin: 0;"><strong>Valid Until:</strong> {valid_until_str}</p>
                    </div>

                    <h3>Itemized Proposal</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th style="text-align: center;">Qty</th>
                                <th style="text-align: right;">Unit Price</th>
                                <th style="text-align: right;">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>

                    <table class="totals">
                        <tr>
                            <td>Subtotal:</td>
                            <td style="font-weight: 500;">${quote.subtotal:.2f}</td>
                        </tr>
                        <tr>
                            <td>Tax ({tax_pct_str}):</td>
                            <td>${quote.tax:.2f}</td>
                        </tr>
                        <tr>
                            <td>Delivery Fee:</td>
                            <td>${quote.delivery_fee:.2f}</td>
                        </tr>
                        <tr>
                            <td>Discount:</td>
                            <td>-${quote.discount:.2f}</td>
                        </tr>
                        <tr class="grand-total">
                            <td>Total:</td>
                            <td>${quote.total:.2f}</td>
                        </tr>
                    </table>

                    {f'<div class="terms"><strong>Notes & Terms:</strong><br>{quote.notes or quote.terms}</div>' if (quote.notes or quote.terms) else ''}
                </div>
                <div class="footer">
                    <p>Thank you for considering {restaurant_name} for your event!</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
CATERING QUOTE #{quote.quote_number}
{restaurant_name}
{contact_info}

Prepared For: {lead_name} {company} ({lead_email})
Event Type: {event_type_str}
Event Date: {event_date_str}
Guest Count: {quote.guest_count} guests
Valid Until: {valid_until_str}

PROPOSAL ITEMS:
{items_text}

Subtotal: ${quote.subtotal:.2f}
Tax ({tax_pct_str}): ${quote.tax:.2f}
Delivery Fee: ${quote.delivery_fee:.2f}
Discount: -${quote.discount:.2f}
TOTAL: ${quote.total:.2f}

{f"Notes & Terms: {quote.notes or quote.terms}" if (quote.notes or quote.terms) else ""}

Thank you for considering {restaurant_name}!
        """.strip()

        return html_body, text_body
