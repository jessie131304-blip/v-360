# 20 Demo Cases

This version auto-populates 20 demo review cases when the database is empty.

The seed set includes:
- Positive cases
- Negative cases
- Mixed cases
- Delivery issues
- Packaging issues
- Price complaints
- Customer service complaints
- Ordering/payment issues
- Product quality issues
- Low-confidence / sarcasm exception
- High-severity approval cases
- Critical safety case
- Multi-department case
- One completed human verification path
- One reject → re-plan → approve path

The seed function runs only when the cases table is empty, so it will not duplicate data during normal restarts.

If the database is reset or a fresh Render instance starts with an empty database, the 20 demo cases will be created automatically.
