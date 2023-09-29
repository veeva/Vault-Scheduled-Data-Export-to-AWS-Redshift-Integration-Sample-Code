def create_sql_str(fields_dict:dict) -> str:
    sql_str = ""
    for k, v in fields_dict.items():
        if v in ("ID", "id"):
            sql_str += f'"{k}" VARCHAR, '
        elif v in ("DateTime", "Date"):
            sql_str += f'"{k}" TIMESTAMPTZ, '
        else:
            sql_str += f'"{k}" VARCHAR, '
    sql_str = sql_str[:-2]
    return sql_str
