from journal_generator import Journal
import pandas as pd

class InventoryGenerator(Journal):
    def generate(self, file):
        df = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                "등록상품 ID": "등록상품ID",
                "옵션 ID": "옵션ID",
            },
            header=(0)
        )

        try:
            journal_rows=[]
            required_columns=[
                "등록상품ID",  "옵션ID", "등록상품명"
            ]
            df = df[required_columns].dropna()
            base_fields=["등록상품ID", "옵션ID", "등록상품명"]

            for _,row in df.iterrows():
                base_info = self._build_base_info(row, base_fields)
                journal_rows.append({
                **base_info})

            return pd.DataFrame(journal_rows)

        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()