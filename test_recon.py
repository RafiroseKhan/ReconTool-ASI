import sys
import traceback
from src.core.coordinator import ReconCoordinator

coordinator = ReconCoordinator()
try:
    coordinator.run_full_recon(
        r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\requirements\System1.csv",
        r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\requirements\System2.csv",
        "Deal Id",
        {"Deal Id": "Trade Id"},
        r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\requirements\Result_Test.xlsx",
        0.01,
        set()
    )
    print("Success")
except Exception as e:
    traceback.print_exc()
