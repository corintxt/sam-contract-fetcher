def process_data(raw_data):
    processed_data = []

    for item in raw_data:
        processed_item = {
            "notice_id": item.get("noticeId", ""),
            "title": item.get("title", ""),
            "solicitation_number": item.get("solicitationNumber", ""),
            "posted_date": item.get("postedDate", ""),
            "response_deadline": item.get("responseDeadLine", ""),
            "type": item.get("type", ""),
            "naics_code": item.get("naicsCode", ""),
            "classification_code": item.get("classificationCode", ""),
            "active": item.get("active", ""),
            "organization_path": item.get("fullParentPathName", ""),
            "office_city": item.get("officeAddress", {}).get("city", ""),
            "office_state": item.get("officeAddress", {}).get("state", ""),
            "office_zip": item.get("officeAddress", {}).get("zipcode", ""),
            "contact_email": item.get("pointOfContact", [{}])[0].get("email", ""),
            "contact_phone": item.get("pointOfContact", [{}])[0].get("phone", ""),
            "contact_name": item.get("pointOfContact", [{}])[0].get("fullName", ""),
            "ui_link": item.get("uiLink", ""),
            "set_aside_type": item.get("typeOfSetAsideDescription", "")
        }
        processed_data.append(processed_item)

    return processed_data