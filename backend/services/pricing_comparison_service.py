import io
import csv
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from sqlalchemy import and_
from sqlalchemy.orm import Session

class PricingComparisonService:
    def calculate_pricing_comparison(
        self,
        db: Session,
        product_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        competitor_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates pricing comparison metrics for a product.
        If start_date or end_date is provided, queries history entries.
        Otherwise queries the latest active competitor price records.
        """
        from main import Product, CompetitorPrice, CompetitorPriceHistory
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        our_price = product.current_price or 0.0

        # Query entries
        use_history = start_date is not None or end_date is not None

        if use_history:
            query = db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id == product_id)
            if start_date:
                query = query.filter(CompetitorPriceHistory.last_checked >= start_date)
            if end_date:
                query = query.filter(CompetitorPriceHistory.last_checked <= end_date)
            if competitor_filter:
                query = query.filter(CompetitorPriceHistory.competitor_name == competitor_filter)
            records = query.order_by(CompetitorPriceHistory.last_checked.desc()).all()
        else:
            query = db.query(CompetitorPrice).filter(CompetitorPrice.product_id == product_id)
            if competitor_filter:
                query = query.filter(CompetitorPrice.competitor_name == competitor_filter)
            records = query.order_by(CompetitorPrice.competitor_price.asc()).all()

        # Filter out records without valid prices
        valid_records = [r for r in records if r.competitor_price is not None]
        prices_list = [r.competitor_price for r in valid_records]
        competitor_count = len(prices_list)

        # Default empty statistics
        stats = {
            "product_id": product_id,
            "product_name": product.name,
            "our_current_price": our_price,
            "competitor_count": competitor_count,
            "lowest_competitor_price": 0.0,
            "highest_competitor_price": 0.0,
            "average_competitor_price": 0.0,
            "median_competitor_price": 0.0,
            "price_gap_absolute": 0.0,
            "price_gap_percent": 0.0,
            "cheaper_competitor_count": 0,
            "higher_competitor_count": 0,
            "equal_price_count": 0,
            "market_position": "no_competitors",
            "market_position_rank": "N/A",
            "competitive_pressure": 0.0,
            "price_range": 0.0,
            "generated_at": datetime.utcnow(),
            "listings": [],
            "insights": []
        }

        if competitor_count == 0:
            stats["insights"] = ["No active competitor pricing registered for this product."]
            return stats

        # Calculations
        lowest = min(prices_list)
        highest = max(prices_list)
        average = sum(prices_list) / competitor_count

        # Median calculation
        sorted_prices = sorted(prices_list)
        n = competitor_count
        if n % 2 == 1:
            median = sorted_prices[n // 2]
        else:
            median = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2.0

        price_gap_abs = our_price - average
        price_gap_pct = (price_gap_abs / average) * 100 if average > 0 else 0.0

        cheaper_count = sum(1 for p in prices_list if p < our_price)
        higher_count = sum(1 for p in prices_list if p > our_price)
        equal_count = sum(1 for p in prices_list if p == our_price)
        price_range = highest - lowest
        competitive_pressure = (cheaper_count / competitor_count) * 100

        # Market position ranking tag
        if our_price < lowest:
            market_pos = "lowest"
        elif our_price > highest:
            market_pos = "highest"
        else:
            if cheaper_count > higher_count:
                market_pos = "upper_mid"
            elif higher_count > cheaper_count:
                market_pos = "lower_mid"
            else:
                market_pos = "median"

        rank_index = cheaper_count + 1
        market_pos_rank = f"{rank_index} of {competitor_count + 1}"

        # Construct detailed listings mapping
        listings = []
        for r in valid_records:
            gap_abs = our_price - r.competitor_price
            gap_pct = (gap_abs / r.competitor_price) * 100 if r.competitor_price > 0 else 0.0
            
            listings.append({
                "competitor_name": r.competitor_name,
                "competitor_product_name": getattr(r, "competitor_product_name", f"{r.competitor_name} SKU"),
                "competitor_price": r.competitor_price,
                "price_gap_absolute": gap_abs,
                "price_gap_percent": gap_pct,
                "availability": getattr(r, "availability", "In Stock"),
                "last_checked": r.last_checked
            })

        # Generate insights
        insights = []
        insights.append(
            f"Our price of INR {our_price:,.2f} is {abs(price_gap_pct):.1f}% "
            f"{'above' if price_gap_abs > 0 else 'below'} the market average of INR {average:,.2f}."
        )

        if cheaper_count > 0:
            insights.append(
                f"{cheaper_count} of {competitor_count} monitored competitors are cheaper than our SKU."
            )
        else:
            insights.append("We are currently matching or beating all monitored competitor prices.")

        # Find competitor name for lowest price
        lowest_record = next((r for r in valid_records if r.competitor_price == lowest), None)
        if lowest_record and lowest < our_price:
            insights.append(
                f"{lowest_record.competitor_name} currently offers the lowest observed price of INR {lowest:,.2f}."
            )

        pressure_level = "high" if competitive_pressure > 50 else "moderate" if competitive_pressure > 20 else "low"
        insights.append(
            f"Competitive pressure is {pressure_level} ({competitive_pressure:.1f}% of competitors undercut our price)."
        )

        stats.update({
            "lowest_competitor_price": lowest,
            "highest_competitor_price": highest,
            "average_competitor_price": average,
            "median_competitor_price": median,
            "price_gap_absolute": price_gap_abs,
            "price_gap_percent": price_gap_pct,
            "cheaper_competitor_count": cheaper_count,
            "higher_competitor_count": higher_count,
            "equal_price_count": equal_count,
            "market_position": market_pos,
            "market_position_rank": market_pos_rank,
            "competitive_pressure": competitive_pressure,
            "price_range": price_range,
            "listings": listings,
            "insights": insights
        })

        return stats

    def calculate_historical_comparison(
        self,
        db: Session,
        product_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        competitor_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves and aggregates chronological price comparisons grouped by day.
        """
        from main import Product, CompetitorPriceHistory
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        our_price = product.current_price or 0.0

        query = db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id == product_id)
        if start_date:
            query = query.filter(CompetitorPriceHistory.last_checked >= start_date)
        if end_date:
            query = query.filter(CompetitorPriceHistory.last_checked <= end_date)
        if competitor_filter:
            query = query.filter(CompetitorPriceHistory.competitor_name == competitor_filter)
        
        records = query.order_by(CompetitorPriceHistory.last_checked.asc()).all()

        # Group by day
        daily_prices: Dict[date, List[float]] = {}
        for r in records:
            if r.competitor_price is None or r.last_checked is None:
                continue
            day = r.last_checked.date()
            if day not in daily_prices:
                daily_prices[day] = []
            daily_prices[day].append(r.competitor_price)

        history_points = []
        for day in sorted(daily_prices.keys()):
            prices = daily_prices[day]
            lowest = min(prices)
            highest = max(prices)
            average = sum(prices) / len(prices)
            
            history_points.append({
                "date": day.strftime("%Y-%m-%d"),
                "our_price": our_price,
                "lowest": lowest,
                "highest": highest,
                "average": average
            })

        return history_points

    def generate_pdf_report(self, stats: Dict[str, Any]) -> bytes:
        """
        Generates a tabular PDF report using ReportLab platypus layouts.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Define clean premium palette styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=6
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=20
        )
        
        header_section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceBefore=15,
            spaceAfter=8
        )

        cell_text_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#334155')
        )

        cell_text_bold = ParagraphStyle(
            'CellTextBold',
            parent=cell_text_style,
            fontName='Helvetica-Bold'
        )

        story = []

        # 1. Header Details
        story.append(Paragraph("Pricing Comparison Report", title_style))
        story.append(Paragraph(
            f"Product ID: {stats['product_id']} | Product SKU: {stats['product_name']} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle_style
        ))

        # 2. KPI Summary table
        story.append(Paragraph("Summary Pricing Statistics", header_section_style))
        
        summary_data = [
            [
                Paragraph("<b>Our Price:</b>", cell_text_style), 
                Paragraph(f"INR {stats['our_current_price']:,.2f}", cell_text_bold),
                Paragraph("<b>Market Rank:</b>", cell_text_style),
                Paragraph(stats['market_position_rank'], cell_text_bold)
            ],
            [
                Paragraph("<b>Min Competitor:</b>", cell_text_style),
                Paragraph(f"INR {stats['lowest_competitor_price']:,.2f}", cell_text_style),
                Paragraph("<b>Max Competitor:</b>", cell_text_style),
                Paragraph(f"INR {stats['highest_competitor_price']:,.2f}", cell_text_style)
            ],
            [
                Paragraph("<b>Market Average:</b>", cell_text_style),
                Paragraph(f"INR {stats['average_competitor_price']:,.2f}", cell_text_style),
                Paragraph("<b>Market Median:</b>", cell_text_style),
                Paragraph(f"INR {stats['median_competitor_price']:,.2f}", cell_text_style)
            ],
            [
                Paragraph("<b>Price Gap Avg:</b>", cell_text_style),
                Paragraph(f"INR {stats['price_gap_absolute']:+,.2f} ({stats['price_gap_percent']:+.1f}%)", cell_text_bold),
                Paragraph("<b>Competitive Pressure:</b>", cell_text_style),
                Paragraph(f"{stats['competitive_pressure']:.1f}%", cell_text_bold)
            ]
        ]
        
        summary_table = Table(summary_data, colWidths=[120, 150, 120, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 15))

        # 3. Dynamic Insights section
        story.append(Paragraph("Key Market Insights", header_section_style))
        for insight in stats["insights"]:
            story.append(Paragraph(f"&bull; {insight}", cell_text_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 15))

        # 4. Detailed Competitor catalog table
        story.append(Paragraph("Competitor Price Matrix Detail", header_section_style))
        
        matrix_data = [
            [
                Paragraph("<b>Competitor Name</b>", cell_text_bold),
                Paragraph("<b>Competitor Product SKU</b>", cell_text_bold),
                Paragraph("<b>Price</b>", cell_text_bold),
                Paragraph("<b>Price Gap</b>", cell_text_bold),
                Paragraph("<b>Gap %</b>", cell_text_bold),
                Paragraph("<b>Availability</b>", cell_text_bold)
            ]
        ]

        for lst in stats["listings"]:
            gap_color = '#EF4444' if lst['price_gap_absolute'] > 0 else '#10B981' if lst['price_gap_absolute'] < 0 else '#64748B'
            gap_style = ParagraphStyle(
                'GapColorStyle',
                parent=cell_text_bold,
                textColor=colors.HexColor(gap_color)
            )

            matrix_data.append([
                Paragraph(lst['competitor_name'], cell_text_style),
                Paragraph(lst['competitor_product_name'], cell_text_style),
                Paragraph(f"INR {lst['competitor_price']:,.2f}", cell_text_style),
                Paragraph(f"INR {lst['price_gap_absolute']:+,.2f}", gap_style),
                Paragraph(f"{lst['price_gap_percent']:+.1f}%", gap_style),
                Paragraph(lst['availability'], cell_text_style)
            ])

        matrix_table = Table(matrix_data, colWidths=[90, 160, 80, 80, 60, 70])
        
        table_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ]
        
        # Alternating row colors
        for i in range(1, len(matrix_data)):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#F8FAFC')))
                
        matrix_table.setStyle(TableStyle(table_style))
        story.append(matrix_table)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_csv_report(self, stats: Dict[str, Any]) -> str:
        """
        Generates a detailed CSV report containing the pricing comparison listings.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write Header Metadata
        writer.writerow(["Pricing Comparison Report"])
        writer.writerow(["Product ID", stats["product_id"]])
        writer.writerow(["Product Name", stats["product_name"]])
        writer.writerow(["Our Price", stats["our_current_price"]])
        writer.writerow(["Generated At", stats["generated_at"].strftime("%Y-%m-%d %H:%M UTC")])
        writer.writerow([])

        # Write Summary Stats Section
        writer.writerow(["Market Statistics Summary"])
        writer.writerow(["Statistic", "Value"])
        writer.writerow(["Competitor Count", stats["competitor_count"]])
        writer.writerow(["Lowest Competitor Price", stats["lowest_competitor_price"]])
        writer.writerow(["Highest Competitor Price", stats["highest_competitor_price"]])
        writer.writerow(["Average Competitor Price", stats["average_competitor_price"]])
        writer.writerow(["Median Competitor Price", stats["median_competitor_price"]])
        writer.writerow(["Price Gap Absolute (Our Price - Avg)", stats["price_gap_absolute"]])
        writer.writerow(["Price Gap Percent", stats["price_gap_percent"]])
        writer.writerow(["Competitive Pressure %", stats["competitive_pressure"]])
        writer.writerow(["Market Position Rank", stats["market_position_rank"]])
        writer.writerow([])

        # Write Listings Header
        writer.writerow([
            "Competitor Name",
            "Competitor Product SKU",
            "Competitor Price",
            "Price Gap Absolute",
            "Price Gap Percent",
            "Availability",
            "Timestamp"
        ])

        for lst in stats["listings"]:
            writer.writerow([
                lst["competitor_name"],
                lst["competitor_product_name"],
                lst["competitor_price"],
                lst["price_gap_absolute"],
                lst["price_gap_percent"],
                lst["availability"],
                lst["last_checked"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(lst["last_checked"], datetime) else str(lst["last_checked"])
            ])

        return output.getvalue()
