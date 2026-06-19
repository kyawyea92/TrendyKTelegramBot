import os
import logging
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_sheet = None


def _get_sheet():
    """Initialize and return the first worksheet of the Google Sheet."""
    global _sheet
    if _sheet is not None:
        return _sheet

    email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    raw_key = os.getenv("GOOGLE_PRIVATE_KEY", "")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    if not (email and raw_key and sheet_id):
        raise RuntimeError(
            "❌ Google Sheets credentials missing. "
            "Check GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_PRIVATE_KEY and GOOGLE_SHEET_ID in .env"
        )

    # Clean up strings if wrapped in quotes on platforms like Railway
    email = email.strip().strip('"\'')
    raw_key = raw_key.strip().strip('"\'')
    sheet_id = sheet_id.strip().strip('"\'')

    # Handle escaped newlines stored in .env (including double escaped \\n from platforms like Railway)
    private_key = raw_key.replace("\\\\n", "\n").replace("\\n", "\n")

    # Derive project_id from service account email (user@project-id.iam.gserviceaccount.com)
    project_id = os.getenv("GOOGLE_PROJECT_ID", "")
    if not project_id and "@" in email and ".iam.gserviceaccount.com" in email:
        project_id = email.split("@")[1].replace(".iam.gserviceaccount.com", "")

    creds = Credentials.from_service_account_info(
        {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": "key",
            "private_key": private_key,
            "client_email": email,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=SCOPES,
    )

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    _sheet = spreadsheet.sheet1  # First worksheet
    logger.info(f"✅ Connected to Google Sheet: {spreadsheet.title}")
    return _sheet


def get_all_products() -> list[dict]:
    """Fetch all rows from the sheet and return as a list of product dicts."""
    try:
        sheet = _get_sheet()
        rows = sheet.get_all_records()  # List of {header: value} dicts
        products = []
        for idx, row in enumerate(rows):
            name = str(row.get("Product Name", "")).strip()
            if not name:
                continue
            available_str = str(row.get("Available Count", "")).strip()
            try:
                available_count = int(float(available_str))
            except (ValueError, TypeError):
                available_count = 0
            if available_count <= 0:
                continue
            product_code = str(row.get("Product_Code") or "").strip()
            # Use row index as unique ID to avoid collisions when Product Code is empty
            unique_id = f"row_{idx}"
            products.append(
                {
                    "id": unique_id,
                    "product_code": product_code,
                    "name": name,
                    "category": str(row.get("Brand Name", "")).strip(),
                    "weight": str(row.get("Size", "")).strip(),
                    "available": available_str,
                    "branch": str(row.get("Branch", "")).strip(),
                    "expiry": str(row.get("Expiry Date", "")).strip(),
                }
            )
        return products
    except Exception as exc:
        logger.error(f"❌ Error fetching products: {exc}", exc_info=True)
        return []


def get_categories() -> list[str]:
    """Return a sorted, deduplicated list of category (Brand Name) values."""
    products = get_all_products()
    seen = []
    for p in products:
        cat = p["category"]
        if cat and cat not in seen:
            seen.append(cat)
    return sorted(seen)


def get_products_by_category(category: str) -> list[dict]:
    return [p for p in get_all_products() if p["category"] == category]


def get_product_by_id(product_id: str) -> dict | None:
    for p in get_all_products():
        if p["id"] == product_id:
            return p
    return None


_customer_spreadsheet = None


def _get_customer_spreadsheet():
    """Initialize and return the customer spreadsheet."""
    global _customer_spreadsheet
    if _customer_spreadsheet is not None:
        return _customer_spreadsheet

    email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    raw_key = os.getenv("GOOGLE_PRIVATE_KEY", "")
    sheet_id = os.getenv("GOOGLE_CUSTOMER_SHEET_ID")

    if not (email and raw_key and sheet_id):
        raise RuntimeError(
            "❌ Google Customer Sheet credentials missing. "
            "Check GOOGLE_CUSTOMER_SHEET_ID in .env"
        )

    # Clean up strings if wrapped in quotes on platforms like Railway
    email = email.strip().strip('"\'')
    raw_key = raw_key.strip().strip('"\'')
    sheet_id = sheet_id.strip().strip('"\'')

    # Handle escaped newlines stored in .env (including double escaped \\n from platforms like Railway)
    private_key = raw_key.replace("\\\\n", "\n").replace("\\n", "\n")

    # Derive project_id from service account email (user@project-id.iam.gserviceaccount.com)
    project_id = os.getenv("GOOGLE_PROJECT_ID", "")
    if not project_id and "@" in email and ".iam.gserviceaccount.com" in email:
        project_id = email.split("@")[1].replace(".iam.gserviceaccount.com", "")

    creds = Credentials.from_service_account_info(
        {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": "key",
            "private_key": private_key,
            "client_email": email,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=SCOPES,
    )

    client = gspread.authorize(creds)
    _customer_spreadsheet = client.open_by_key(sheet_id)
    return _customer_spreadsheet


def save_order_record(order_id: str, date_str: str, customer: dict, items: list, payment: dict, tracking_number: str = ""):
    """Saves customer info and order items to two separate worksheets in the Google Spreadsheet."""
    try:
        spreadsheet = _get_customer_spreadsheet()
        worksheets = spreadsheet.worksheets()
        
        if len(worksheets) < 2:
            raise RuntimeError("The customer spreadsheet needs at least 2 sheets (tabs).")
            
        customer_sheet = worksheets[0]
        items_sheet = worksheets[1]
        
        # Check if Tracking Number header exists, if not add it at column 12
        headers = customer_sheet.row_values(1)
        if "Tracking Number" not in headers:
            try:
                customer_sheet.update_cell(1, 12, "Tracking Number")
            except Exception as e:
                logger.warning(f"⚠️ Could not add Tracking Number header: {e}")
        
        # Save to Customer Info
        customer_row = [
            order_id,
            date_str,
            customer.get("name", ""),
            customer.get("address", ""),
            customer.get("phone1", ""),
            customer.get("phone2", ""),
            payment.get("type", ""),
            payment.get("method", ""),
            "Yes" if payment.get("delivery_paid") else "No",
            payment.get("delivery_amount", 0),
            payment.get("other_amount", 0),
            tracking_number
        ]
        customer_sheet.append_row(customer_row)
        
        # Save to Order Items
        item_rows = []
        for item in items:
            item_rows.append([
                order_id,
                item.get("name", ""),
                item.get("count", 0),
                item.get("price", 0),
                item.get("total", 0)
            ])
        items_sheet.append_rows(item_rows)
        
        logger.info(f"✅ Successfully saved order {order_id} to Google Sheets.")
    except Exception as exc:
        logger.error(f"❌ Error saving order to Google Sheets: {exc}", exc_info=True)
        raise exc


def reduce_stock(items: list):
    """Reduce the Available Count in the product stock sheet for each ordered item."""
    try:
        sheet = _get_sheet()
        header_row = sheet.row_values(1)
        
        # Find Available Count column index (1-based for gspread)
        avail_col = None
        for i, h in enumerate(header_row):
            if h.strip() == "Available Count":
                avail_col = i + 1
        
        if avail_col is None:
            logger.error("❌ Could not find 'Available Count' column in stock sheet.")
            return
        
        for item in items:
            product_id = str(item.get("id", "")).strip()
            ordered_count = item.get("count", 0)
            
            if not product_id or ordered_count <= 0:
                continue
            
            # Extract row index from the unique id (format: row_X)
            if product_id.startswith("row_"):
                try:
                    row_idx = int(product_id[4:])
                    cell_row = row_idx + 2  # +1 for 0-based index, +1 for header row
                    current_val = sheet.cell(cell_row, avail_col).value
                    try:
                        current_count = int(current_val)
                    except (ValueError, TypeError):
                        current_count = 0
                    
                    new_count = max(0, current_count - ordered_count)
                    sheet.update_cell(cell_row, avail_col, new_count)
                    logger.info(f"📦 Stock updated: {item.get('name', product_id)} → {current_count} → {new_count}")
                except (ValueError, IndexError) as e:
                    logger.warning(f"⚠️ Could not parse row index from id '{product_id}': {e}")
        
        logger.info("✅ Stock reduction complete.")
    except Exception as exc:
        logger.error(f"❌ Error reducing stock: {exc}", exc_info=True)
        raise exc
