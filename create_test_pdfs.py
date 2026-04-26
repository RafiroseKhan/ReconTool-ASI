import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import os

# Create sample data
data = {
    'TradeID': ['TRD-001', 'TRD-002', 'TRD-003'],
    'Client': ['Nedbank', 'Standard Bank', 'Absa'],
    'Amount': ['1,500.00', '2,350.50', '800.00'],
    'Status': ['Settled', 'Pending', 'Failed']
}
df = pd.DataFrame(data)

# 1. Create Native PDF (Text embedded)
fig, ax = plt.subplots(figsize=(6, 2))
ax.axis('tight')
ax.axis('off')
table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
table.scale(1, 1.5)
plt.savefig('C:\\Users\\RafiroseKhanShah\\ReconTool-ASI\\sample_native.pdf', format='pdf', bbox_inches='tight')
plt.close()

# 2. Create Scanned PDF (Image embedded)
fig, ax = plt.subplots(figsize=(6, 2))
ax.axis('tight')
ax.axis('off')
table = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
table.scale(1, 1.5)
plt.savefig('C:\\Users\\RafiroseKhanShah\\ReconTool-ASI\\temp_table.png', format='png', bbox_inches='tight')
plt.close()

# Convert PNG to PDF to simulate a scanned document
img = Image.open('C:\\Users\\RafiroseKhanShah\\ReconTool-ASI\\temp_table.png')
img_converted = img.convert('RGB')
img_converted.save('C:\\Users\\RafiroseKhanShah\\ReconTool-ASI\\sample_scanned.pdf')
os.remove('C:\\Users\\RafiroseKhanShah\\ReconTool-ASI\\temp_table.png')

print("Created sample_native.pdf and sample_scanned.pdf")