import sys
import traceback
from src.core.coordinator import ReconCoordinator

coordinator = ReconCoordinator()
try:
    coordinator.run_full_recon(
        r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\data\Folder B\source_a.csv",
        r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\data\Folder B\source_b.csv",
        "Trade_Id",
        {"Trade_Id": "Trade Id"},
        r"C:\Users\RuhiKhanna\.openclaw\workspace\ReconTool-ASI\data\Result_Test.xlsx",
        0.01,
        set()
    )
    print("Success")
except Exception as e:
    traceback.print_exc()
