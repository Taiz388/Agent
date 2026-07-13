from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generator import generate_contract_docx
from src.utils import load_contract_config
from src.validators import validate_fields


def main() -> None:
    config = load_contract_config()
    contract_type = config["contract_types"]["sheet_strip_retail"]
    fields = {
        "contract_no": "BX(LS)26-999",
        "sign_date": "2026-07-08",
        "sign_place": "Nanping",
        "buyer_name": "Demo Buyer Co., Ltd.",
        "buyer_address": "Demo address",
        "seller_name": "Fujian Nanping Aluminium Sheet & Strip Co., Ltd.",
        "product_name": "Aluminium sheet",
        "delivery_place": "Buyer warehouse",
        "delivery_time": "Within 10 days after deposit",
        "payment_terms": "T/T or bank acceptance bill, shipment after payment.",
        "contact_person": "Demo Contact",
        "contact_phone": "13800000000",
        "products": [
            {
                "product_name": "Aluminium sheet",
                "alloy_state": "3003H24",
                "specification": "4.0*1300*1850",
                "weight": "8 MT",
                "processing_fee": "3000 RMB/MT",
                "unit_price": "SMM + processing fee",
                "amount": "Actual settlement",
                "remark": "Smoke test data",
            }
        ],
    }
    issues = validate_fields(contract_type, fields)
    if issues:
        raise SystemExit("validation failed: " + "; ".join(issues))
    path = generate_contract_docx(contract_type, fields, fields["products"])
    print(path)


if __name__ == "__main__":
    main()
