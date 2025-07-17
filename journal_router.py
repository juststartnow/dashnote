# journal_generator.py
import pandas as pd
from journal_generator import SalesJournalGenerator, ShippingJournalGenerator,ReturnPickupRestockingJournalGenerator, InventoryCompensationJournalGenerator, StorageFeeJournalGenerator, ValueAddedServiceFeeJournalGenerator, VreturnHandlingJournalGenerator
import streamlit as st


class JournalRouter:
    def __init__(self):
        self.filetype_map = {
            "CATEGORY_TR" : SalesJournalGenerator,
            "WAREHOUSING_SHIPPING" : ShippingJournalGenerator,
            "CRETURN_PICKUP_RESTOCKING": ReturnPickupRestockingJournalGenerator,
            "INVENTORY_COMPENSATION": InventoryCompensationJournalGenerator,
            "STORAGE_FEE": StorageFeeJournalGenerator,
            "VALUE_ADDED_SERVICE_FEE" : ValueAddedServiceFeeJournalGenerator,
            "VRETURN_HANDLING" : VreturnHandlingJournalGenerator
        }

    def route(self, file, filename):
        print(f"[DEBUG] route() 진입 - filename: {filename}")
        for key, GeneratorClass in self.filetype_map.items():
            if key in filename:
                generator = GeneratorClass()
                result = generator.generate(file, filename)  # df는 쿠팡 엑셀에서 읽은 DataFrame
                st.success(f"✅ '{filename}' 처리 완료")
                return result

        st.warning(f"🚫 파일 '{filename}'에 대한 처리기가 없습니다.")
        return pd.DataFrame()

