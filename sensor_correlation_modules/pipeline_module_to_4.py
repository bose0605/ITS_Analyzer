
import pandas as pd
import os
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import xlsxwriter

def full_logger_ptat_pipeline(
    logger_input_raw,
    ptat_input_raw,
    merged_excel_output,
    ptat_columns=[
        "Time", "Power-IA Power(Watts)", "Power-GT Power(Watts)", "Power-Package Power(Watts)",
        "SEN1-temp(Degree C)", "SEN2-temp(Degree C)", "SEN3-temp(Degree C)",
        "SEN4-temp(Degree C)", "SEN5-temp(Degree C)", "SEN6-temp(Degree C)", "TCPU-CPU-temp(Degree C)"
    ]):

    def convert_to_utf8_csv(input_file):
        filename, ext = os.path.splitext(input_file)
        ext = ext.lower()
        output_file = filename + '_utf8.csv'
        try:
            try:
                with open(input_file, 'rb') as f:
                    first_bytes = f.read(3)
                encoding = 'utf-8-sig' if first_bytes.startswith(b'\xef\xbb\xbf') else 'cp949'
                df = pd.read_csv(input_file, encoding=encoding, low_memory=False)
            except Exception:
                if ext == '.xls':
                    df = pd.read_excel(input_file, engine='xlrd')
                elif ext == '.xlsx':
                    df = pd.read_excel(input_file, engine='openpyxl')
                else:
                    raise
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            return output_file
        except Exception as e:
            return None

    def extract_logger_columns(input_file, min_val=0, max_val=75, time_label="Time"):
        output_file = input_file.replace(".csv", "_selected_columns.csv")
        df = pd.read_csv(input_file, encoding='utf-8-sig', header=None, low_memory=False)
        header_row = df.iloc[8]
        time_row = df.iloc[9]
        data = df.iloc[10:].copy()

        try:
            time_index = list(time_row).index(time_label)
        except ValueError:
            return None, []

        valid_columns = []
        for col in data.columns:
            if col == time_index:
                continue
            try:
                col_values = pd.to_numeric(data[col], errors='coerce').dropna()
                if not col_values.empty and col_values.between(min_val, max_val).all():
                    valid_columns.append(col)
            except Exception:
                continue

        col_indices = [time_index] + valid_columns
        selected_data = data.iloc[:, col_indices]
        selected_headers = header_row[col_indices].copy()
        selected_headers.iloc[0] = time_label
        selected_data.columns = selected_headers
        selected_data.to_csv(output_file, index=False, encoding='utf-8-sig')
        return output_file, selected_headers[1:].tolist()

    def merge_and_save(logger_path, ptat_path, output_excel):
        df_logger = pd.read_csv(logger_path, encoding='utf-8-sig')
        df_ptat = pd.read_csv(ptat_path, encoding='utf-8-sig')

        df_logger["Time"] = pd.to_datetime(df_logger["Time"], format="%H:%M:%S", errors='coerce')
        df_ptat["Time"] = df_ptat["Time"].astype(str).str.strip().str.split(":").str[:3].str.join(":")
        df_ptat = df_ptat[ptat_columns]
        df_ptat["Time"] = pd.to_datetime(df_ptat["Time"], format="%H:%M:%S", errors='coerce')

        df_logger.dropna(subset=["Time"], inplace=True)
        df_ptat.dropna(subset=["Time"], inplace=True)

        start_time = max(df_logger["Time"].min(), df_ptat["Time"].min())
        df_logger = df_logger[df_logger["Time"] >= start_time].copy()
        df_ptat = df_ptat[df_ptat["Time"] >= start_time].copy()

        df_logger["Time"] = df_logger["Time"].dt.strftime("%H:%M:%S")
        df_ptat["Time"] = df_ptat["Time"].dt.strftime("%H:%M:%S")

        merged_df = pd.merge(df_ptat, df_logger, on="Time", how="inner")
        return merged_df

    def cluster_and_export(df, excel_path):
        df["Time"] = pd.to_datetime(df["Time"], format="%H:%M:%S", errors='coerce')
        df = df.dropna(subset=["Time", "Power-Package Power(Watts)"]).reset_index(drop=True)
        df["Power_Smoothed"] = df["Power-Package Power(Watts)"].rolling(10, min_periods=1).mean()
        kmeans = KMeans(n_clusters=4, random_state=42, n_init='auto')
        df["Cluster"] = kmeans.fit_predict(df[["Power_Smoothed"]])

        cluster_df = df[df["Cluster"] == 1].copy().reset_index(drop=True)
        avg_powers = []
        for i in range(len(cluster_df)):
            t = cluster_df.loc[i, "Time"]
            future = cluster_df[(cluster_df["Time"] >= t) & (cluster_df["Time"] <= t + pd.Timedelta(seconds=5))]
            avg_powers.append(future["Power-Package Power(Watts)"].mean() if not future.empty else None)

        cluster_df["Power_5s_Avg"] = avg_powers
        cluster_df["Power_Jump"] = cluster_df["Power_5s_Avg"] - cluster_df["Power-Package Power(Watts)"]

        jump_candidates = cluster_df[cluster_df["Power_Jump"].notna()].copy()
        jump_candidates = jump_candidates[jump_candidates["Power_Jump"] > 0]
        jump_candidates = jump_candidates.sort_values("Power_Jump", ascending=False).reset_index()

        selected_jumps = []
        min_index_gap = 30
        for idx in jump_candidates.index:
            i = jump_candidates.loc[idx, "index"]
            if all(abs(i - j) >= min_index_gap for j in selected_jumps):
                selected_jumps.append(i)
            if len(selected_jumps) == 4:
                break

        selected_jumps = sorted(selected_jumps)
        split_indices = selected_jumps + [len(cluster_df)]
        experiment_labels = ["TAT+Fur", "TAT", "Fur", "Prime95"]

        cluster_df["Experiment"] = None
        for i in range(len(split_indices) - 1):
            start, end = split_indices[i], split_indices[i+1]
            cluster_df.loc[start:end - 1, "Experiment"] = experiment_labels[i]

        df_with_exp = pd.merge_asof(
            df.sort_values("Time"),
            cluster_df[["Time", "Experiment"]].dropna().sort_values("Time"),
            on="Time",
            direction="backward"
        )

        image_path = excel_path.replace(".xlsx", "_graph.png")
        colors = ['blue', 'green', 'orange', 'red']
        plt.figure(figsize=(14, 6))
        for i in range(len(split_indices) - 1):
            start, end = split_indices[i], split_indices[i+1]
            segment = cluster_df.iloc[start:end]
            plt.plot(segment["Time"], segment["Power-Package Power(Watts)"], label=experiment_labels[i], color=colors[i])
        for idx in selected_jumps:
            plt.axvline(cluster_df.loc[idx, "Time"], color='black', linestyle='--')
        plt.title("Cluster 1: 4 Experiments (Power Jump Based Segmentation)")
        plt.xlabel("Time")
        plt.ylabel("Power-Package Power(Watts)")
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(image_path)
        plt.close()

        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Full Data', index=False)
            cluster_df.to_excel(writer, sheet_name='Cluster 1 Split', index=False)
            df_with_exp.to_excel(writer, sheet_name='Experiment Labeled', index=False)
            workbook = writer.book
            worksheet = workbook.add_worksheet('Graph')
            worksheet.insert_image('B2', image_path)

    logger_utf8 = convert_to_utf8_csv(logger_input_raw)
    ptat_utf8 = convert_to_utf8_csv(ptat_input_raw)
    if not logger_utf8 or not ptat_utf8:
        return None, []

    logger_filtered, logger_targets = extract_logger_columns(logger_utf8)
    if not logger_filtered:
        return None, []

    merged_df = merge_and_save(logger_filtered, ptat_utf8, merged_excel_output)
    cluster_and_export(merged_df, merged_excel_output)
    return merged_df, logger_targets
