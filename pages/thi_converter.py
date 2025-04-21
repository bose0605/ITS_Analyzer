import pandas as pd
import re

def convert_thi_txt_to_df(file_content: str) -> pd.DataFrame:
    header = [
        "Count", "AC", "TM", "L0", "L1", "L2", "L3", "Fan", "ATM", "CPU",
        "S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9",
        "Sa", "Sb", "Sc", "Sd", "Se", "Sf", "Time"
    ]

    data = []
    lines = file_content.splitlines()

    for line in lines:
        if re.match(r"^\s*\d+", line):
            tokens = re.split(r"\s+", line.strip())
            try:
                if len(tokens) > 8 and tokens[7].endswith("/"):
                    tokens[7] = tokens[8]
                    del tokens[8]
                if len(tokens) > 9 and "/" not in tokens[8]:
                    tokens[8] = tokens[8] + tokens[9]
                    del tokens[9]
                if len(tokens) > 8:
                    tokens[8] = f"'{tokens[8]}"
                if re.match(r"\d{2}:\d{2}:\d{2}$", tokens[-1]):
                    time_value = tokens[-1]
                else:
                    time_value = ""
                tokens = tokens[:27]
                if len(tokens) == 27:
                    tokens[-1] = time_value
                    data.append(tokens)
            except:
                continue

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=header)
    df["ATM"] = df["ATM"].astype(str)
    return df
