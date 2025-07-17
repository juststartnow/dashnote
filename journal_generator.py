import pandas as pd
from abc import ABC, abstractmethod
from account_rules import account_rules


class Journal(ABC):
    def _prepare_sheet(self, file, sheet_index=0, rename_dict=None, header=(0,)):
        """
        공통 시트 전처리 함수

        :param file: 업로드된 엑셀 파일 객체
        :param sheet_index: 읽을 시트 번호
        :param rename_dict: 컬럼명 변경을 위한 dict (필요 시)
        :param header: 헤더 위치 (int 또는 tuple)
        :return: 전처리된 DataFrame
        """
        # tuple이든 int든 그대로 전달
        df = pd.read_excel(file, sheet_name=sheet_index, header=header)

        # 헤더가 다중일 경우: 컬럼 이름을 결합
        if isinstance(header, (list, tuple)):
            df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
        else:
            df.columns = [str(col).strip() for col in df.columns]

        # 컬럼명 변경
        if rename_dict:
            df = df.rename(columns=rename_dict)

        # 숫자형 int로 변경
        for col in ["주문ID", "옵션ID", "등록상품ID"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        return df

    def _build_base_info(self, row, fields):
        """공통 필드 추출 (없으면 빈 문자열 처리)"""
        return {field: row[field] if field in row else "" for field in fields}
    
    def _append_lines(self, journal_rows, base_info, journal_source, lines, filename):
        """공통 분개 처리 루프"""
        for drcr, account, amt in lines:
            journal_rows.append({
                **base_info,
                "원천": journal_source,
                "차대구분": drcr,
                "계정코드": account_rules.inverse[account],
                "금액": int(amt),
                "파일명": filename
            })

    def _process_entries(self, df, required_columns, base_fields, entry_callback, filename=None):
        journal_rows=[]
        df = df[required_columns].dropna()

        for _,row in df.iterrows():
            base_info = self._build_base_info(row, base_fields)
            for journal_source, lines in entry_callback(row):
                self._append_lines(journal_rows, base_info, journal_source, lines, filename)

        return journal_rows
    

    @abstractmethod
    def generate(self, file, filename=None):
        """전표 객체를 생성하는 추상 메서드"""
        pass

class SalesJournalGenerator(Journal):
    def generate(self, file, filename):
        df = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                "매출인식일": "일자"
            },
            header=(1)
        )

        try:
            def make_sales_entries(row):
                amount = int(row["매출금액(A*B-C)"])
                main_credit = round(amount / 1.1, 0)
                vat_credit = amount - main_credit

                return [
                    ("차변", "외상매출금", amount),
                    ("대변", "상품매출", main_credit),
                    ("대변", "예수부가세", vat_credit)
                ]

            def make_fee_entries(row):
                fee = int(row["판매수수료"])
                feevat = int(row["판매수수료 VAT"])

                return [
                    ("차변", "판매수수료", fee),
                    ("차변", "선급부가세", feevat),
                    ("대변", "외상매입금", fee + feevat)
                ]

            def entry_callback(row):
                return [
                    ("AR", make_sales_entries(row)),
                    ("AP", make_fee_entries(row))
                ]
            
            rows = self._process_entries(
                df,
                required_columns=["일자","주문ID", "옵션ID", "매출금액(A*B-C)", "판매수수료", "판매수수료 VAT"],
                base_fields=["일자","옵션ID", "주문ID"],
                entry_callback=entry_callback,
                filename = filename
            )
            return pd.DataFrame(rows)

        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()
        
class ShippingJournalGenerator(Journal):
    def generate(self, file, filename):
        df1 = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                    "주문ID_Unnamed: 6_level_1": "주문ID",
                    "옵션ID_Unnamed: 10_level_1": "옵션ID",
                    "매출인식일_Unnamed: 4_level_1": "일자"
            },
            header=(6,7)
        )

        df2 = self._prepare_sheet(
            file,
            sheet_index=1,
            rename_dict={
                    "주문ID_Unnamed: 6_level_1": "주문ID",
                    "옵션ID_Unnamed: 10_level_1": "옵션ID",
                    "매출인식일_Unnamed: 4_level_1": "일자"
            },
            header=(6,7)
        )


        try:
            def entry_callback1(row):
                amount = int(row["쿠팡풀필먼트서비스(CFS) 입출고비_발생비용(A)"])
                amount_discount = int(row["쿠팡풀필먼트서비스(CFS) 입출고비_할인가(B)"])
                amount_total = int(row["쿠팡풀필먼트서비스(CFS) 입출고비_할인적용가(A-B)"])
                main_credit = round(amount_total / 1.1, 0)
                input_vat = amount_total - main_credit

                return [
                    ("AP", [
                        ("차변", "입출고비", amount),
                        ("차변", "입출고비_할인", -amount_discount),
                        ("차변", "선급부가세", input_vat),
                        ("대변", "외상매입금", amount_total+input_vat)
                    ]),
                ]
            
            rows1 = self._process_entries(
                df1,
                required_columns=[
                    "일자", "주문ID", "옵션ID",
                    "쿠팡풀필먼트서비스(CFS) 입출고비_발생비용(A)",
                    "쿠팡풀필먼트서비스(CFS) 입출고비_할인가(B)",
                    "쿠팡풀필먼트서비스(CFS) 입출고비_할인적용가(A-B)"
                ],
                base_fields=["일자", "옵션ID", "주문ID"],
                entry_callback=entry_callback1
            )

            def entry_callback2(row):
                amount = int(row["쿠팡풀필먼트서비스(CFS) 배송비_발생비용(A)"])
                amount_discount = int(row["쿠팡풀필먼트서비스(CFS) 배송비_할인가(B)"])
                amount_addedfee = int(row["쿠팡풀필먼트서비스(CFS) 배송비_추가비용"])
                amount_total = amount - amount_discount + amount_addedfee
                main_credit = round(amount_total / 1.1, 0)
                input_vat = amount_total - main_credit

                return [
                    ("AP", [
                        ("차변", "배송비", amount),
                        ("차변", "배송비_할인", -amount_discount),
                        ("차변", "배송비_추가비용", amount_addedfee),
                        ("차변", "선급부가세", input_vat),
                        ("대변", "외상매입금", amount_total + input_vat)
                    ])
                ]

            rows2 = self._process_entries(
                df2,
                required_columns=[
                    "일자", "주문ID", "옵션ID",
                    "쿠팡풀필먼트서비스(CFS) 배송비_발생비용(A)",
                    "쿠팡풀필먼트서비스(CFS) 배송비_할인가(B)",
                    "쿠팡풀필먼트서비스(CFS) 배송비_추가비용"
                ],
                base_fields=["일자", "옵션ID", "주문ID"],
                entry_callback=entry_callback2,
                filename = filename
            )

            return pd.DataFrame(rows1 + rows2)
        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()
        
class ReturnPickupRestockingJournalGenerator(Journal):
    def generate(self, file, filename):
        df1 = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                    "주문ID_Unnamed: 6_level_1": "주문ID",
                    "옵션ID_Unnamed: _level_1": "옵션ID",
                    "매출인식일_Unnamed: 4_level_1": "일자"
            },
            header=(6,7)
        )

        df2 = self._prepare_sheet(
            file,
            sheet_index=1,
            rename_dict={
                    "주문ID_Unnamed: 6_level_1": "주문ID",
                    "옵션ID_Unnamed: 10_level_1": "옵션ID",
                    "매출인식일_Unnamed: 4_level_1": "일자"
            },
            header=(6,7)
        )


        try:
            def entry_callback1(row):
                amount = int(row["쿠팡풀필먼트서비스(CFS) 반품회수비_발생비용(A)"])
                amount_discount = int(row["쿠팡풀필먼트서비스(CFS) 반품회수비_할인가(B)"])
                amount_promotion = int(row["쿠팡풀필먼트서비스(CFS) 반품회수비_무료 프로모션 금액(C)"])
                amount_total = amount-amount_discount-amount_promotion
                main_credit = round(amount_total/ 1.1, 0)
                input_vat = amount_total - main_credit

                return [
                    ("AP", [
                        ("차변", "반품회수비", amount),
                        ("차변", "반품회수비_할인", -amount_discount),
                        ("차변", "반품회수비_무료프로모션", -amount_promotion),
                        ("차변", "선급부가세", input_vat),
                        ("대변", "외상매입금", amount_total+input_vat)
                    ]),
                ]
            
            rows1 = self._process_entries(
                df1,
                required_columns=[
                    "일자", "주문ID", "옵션ID",
                    "쿠팡풀필먼트서비스(CFS) 반품회수비_발생비용(A)",
                    "쿠팡풀필먼트서비스(CFS) 반품회수비_할인가(B)",
                    "쿠팡풀필먼트서비스(CFS) 반품회수비_무료 프로모션 금액(C)"
                ],
                base_fields=["일자", "옵션ID", "주문ID"],
                entry_callback=entry_callback1
            )

            def entry_callback2(row):
                amount = int(row["쿠팡풀필먼트서비스(CFS) 반품재입고비_발생비용(A)"])
                amount_discount = int(row["쿠팡풀필먼트서비스(CFS) 반품재입고비_할인가(B)"])
                amount_promotion = int(row["쿠팡풀필먼트서비스(CFS) 반품재입고비_무료 프로모션 금액(C)"])
                amount_total = amount-amount_discount-amount_promotion
                main_credit = round(amount_total/ 1.1, 0)
                input_vat = amount_total - main_credit

                return [
                    ("AP", [
                        ("차변", "반품재입고비", amount),
                        ("차변", "반품재입고_할인", -amount_discount),
                        ("차변", "반품재입고_무료프로모션", -amount_promotion),
                        ("차변", "선급부가세", input_vat),
                        ("대변", "외상매입금", amount_total+input_vat)
                    ]),
                ]

            rows2 = self._process_entries(
                df2,
                required_columns=[
                    "일자", "주문ID", "옵션ID",
                    "쿠팡풀필먼트서비스(CFS) 반품재입고비_발생비용(A)",
                    "쿠팡풀필먼트서비스(CFS) 반품재입고비_할인가(B)",
                    "쿠팡풀필먼트서비스(CFS) 반품재입고비_무료 프로모션 금액(C)"
                ],
                base_fields=["일자", "옵션ID", "주문ID"],
                entry_callback=entry_callback2,
                filename = filename
            )

            return pd.DataFrame(rows1 + rows2)
        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()
        

class InventoryCompensationJournalGenerator(Journal):
    def generate(self, file, filename):
        df = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                "정산주기(종료일)": "일자"
            },
            header=(1)
        )

        try:
            def inventory_loss_entries(row):
                amount = round(int(row["판매액(A*B) - 부가세"] )* 0.3 , 0)

                return [
                    ("차변", "재고자산감모손실", amount),
                    ("대변", "상품", amount),
                ]

            def inventory_compensation_entries(row):
                compensation = int(row["보상 금액"])

                return [
                    ("대변", "잡이익_재고손실보상", compensation),
                    ("차변", "미수금", compensation)
                ]

            def entry_callback(row):
                return [
                    ("GL", inventory_loss_entries(row)),
                    ("AR", inventory_compensation_entries(row))
                ]
            
            rows = self._process_entries(
                df,
                required_columns=["일자","주문ID", "옵션ID", "판매액(A*B) - 부가세", "보상 금액"],
                base_fields=["일자","옵션ID", "주문ID"],
                entry_callback=entry_callback,
                filename = filename
            )
            return pd.DataFrame(rows)

        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()
        
class StorageFeeJournalGenerator(Journal):
    def generate(self, file, filename):
        df = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                "매출인식일_Unnamed: 4_level_1": "일자",
                "옵션ID_Unnamed: 8_level_1": "옵션ID"
            },
            header=(6,7)
        )

        try:
            def entry_callback1(row):
                amount = int(row["쿠팡풀필먼트서비스(CFS) 보관비_발생비용(A)"])
                amount_discount = int(row["쿠팡풀필먼트서비스(CFS) 보관비_할인가(B)"])
                amount_promotion = int(row["쿠팡풀필먼트서비스(CFS) 보관비_로켓그로스 세이버 혜택 금액(C)"])
                amount_total = amount - amount_discount - amount_promotion
                input_vat = round(amount_total* 0.1, 0)

                return [
                    ("AP", [
                        ("차변", "보관비", amount),
                        ("차변", "보관비_할인", -amount_discount),
                        ("차변", "보관비_프로모션", -amount_promotion),
                        ("차변", "선급부가세", input_vat),
                        ("대변", "외상매입금", amount_total+input_vat)
                    ]),
                ]
            
            rows = self._process_entries(
                df,
                required_columns=[
                    "일자", "옵션ID",
                    "쿠팡풀필먼트서비스(CFS) 보관비_발생비용(A)",
                    "쿠팡풀필먼트서비스(CFS) 보관비_할인가(B)",
                    "쿠팡풀필먼트서비스(CFS) 보관비_로켓그로스 세이버 혜택 금액(C)"
                ],
                base_fields=["일자", "옵션ID", "주문ID"],
                entry_callback=entry_callback1,
                filename = filename
            )

            return pd.DataFrame(rows)

        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()
        
class ValueAddedServiceFeeJournalGenerator(Journal):
    def generate(self, file, filename):
        df = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                "매출인식일_Unnamed: 4_level_1": "일자",
                "옵션ID_Unnamed: 10_level_1": "옵션ID"
            },
            header=(6,7)
        )
        try:
            def entry_callback(row):
                amount = int(row["쿠팡풀필먼트서비스(CFS) 바코드 부가 서비스비_발생비용(A)"])
                amount_discount = int(row["옵션 유형_할인가(B)"])
                amount_total = amount - amount_discount 
                input_vat = round(amount_total* 0.1, 0)

                return [
                    ("AP", [
                        ("차변", "부가서비스비", amount),
                        ("차변", "부가서비스비_할인", -amount_discount),
                        ("차변", "선급부가세", input_vat),
                        ("대변", "외상매입금", amount_total+input_vat)
                    ]),
                ]
            
            rows = self._process_entries(
                df,
                required_columns=[
                    "일자", "옵션ID",
                    "쿠팡풀필먼트서비스(CFS) 바코드 부가 서비스비_발생비용(A)",
                    "옵션 유형_할인가(B)",
                ],
                base_fields=["일자", "옵션ID", "주문ID"],
                entry_callback=entry_callback,
                filename = filename
            )
            
            return pd.DataFrame(rows)

        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()
        
class VreturnHandlingJournalGenerator(Journal):
    def generate(self, file, filename):
        df = self._prepare_sheet(
            file,
            sheet_index=0,
            rename_dict={
                "매출인식일_Unnamed: 4_level_1": "일자",
                "옵션ID_Unnamed: 10_level_1": "옵션ID"
            },
            header=(6,7)
        )
        try:
            def entry_callback(row):
                amount = int(row["쿠팡풀필먼트서비스(CFS) 반출비_발생비용(A)"])
                amount_discount = int(row["쿠팡풀필먼트서비스(CFS) 반출비_할인가(B)"])
                amount_promotion = int(row["쿠팡풀필먼트서비스(CFS) 반출비_무료 프로모션 금액(C)"])
                amount_total = amount - amount_discount - amount_promotion
                input_vat = round(amount_total* 0.1, 0)

                return [
                    ("AP", [
                        ("차변", "반출비", amount),
                        ("차변", "반출비_할인", -amount_discount),
                        ("차변", "반출비_프로모션", -amount_promotion),
                        ("차변", "선급부가세", input_vat),
                        ("대변", "외상매입금", amount_total+input_vat)
                    ]),
                ]
            
            rows = self._process_entries(
                df,
                required_columns=[
                    "일자", "옵션ID",
                    "쿠팡풀필먼트서비스(CFS) 반출비_발생비용(A)",
                    "쿠팡풀필먼트서비스(CFS) 반출비_할인가(B)",
                    "쿠팡풀필먼트서비스(CFS) 반출비_무료 프로모션 금액(C)",
                ],
                base_fields=["일자", "옵션ID", "주문ID"],
                entry_callback=entry_callback,
                filename = filename
            )

            return pd.DataFrame(rows)

        except KeyError as e:
            print(f"[전표 생성 오류] 누락된 열: {e}")
            return pd.DataFrame()
        