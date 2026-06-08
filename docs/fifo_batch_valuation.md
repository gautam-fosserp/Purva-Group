# FIFO Batch Valuation — Functional Documentation

**Module:** Stock / Inventory
**App:** Purva
**Date:** 2026-04-24

---

## 1. What Is This?

This customization ensures that when items are sold, the cost applied follows the **First In, First Out (FIFO)** principle — meaning the cost of the oldest purchase is always consumed first, regardless of which batch the user selects on the transaction.

---

## 2. The Problem It Solves

In standard ERPNext, when an item is tracked by batch, the cost on a sale is taken from the **batch that was selected** on the Delivery Note or Sales Invoice. This means if a user picks a newer (more expensive) batch, the profit calculation uses that batch's cost — even though older (cheaper) stock has not been consumed yet.

This leads to **incorrect profit figures** because the cost of goods sold does not follow the actual purchase order.

### Example

| Purchase | Batch | Qty | Rate |
|---|---|---|---|
| Purchase 1 (older) | Batch A | 10 pcs | ₹10 |
| Purchase 2 (newer) | Batch B | 10 pcs | ₹15 |

User creates a Delivery Note and selects **Batch B** for 5 pcs.

| | Rate Applied | Profit on ₹20 sale price |
|---|---|---|
| **Without fix** | ₹15 (Batch B's rate) | ₹25 |
| **With fix** | ₹10 (oldest purchase first) | ₹50 |

The batch selection on the document is still saved for traceability purposes — only the **cost calculation** changes.

---

## 3. How It Behaves After the Fix

- The **batch field** on Delivery Notes, Sales Invoices, and Stock Entries continues to work as before. Users select batches for tracking purposes (expiry, traceability, quality).
- The **cost of goods sold** is always derived from the oldest available purchase layer, not from the selected batch.
- When the oldest purchase layer is fully consumed, the system **automatically moves to the next layer**.
- If a single sale spans multiple purchase layers (e.g. 15 units sold but the oldest layer only has 10), the system **splits the cost proportionally** across layers and applies a weighted average rate.

---

## 4. Scope

| Applies To | Does Not Apply To |
|---|---|
| Items with FIFO valuation method | Items with Moving Average valuation |
| All batch-tracked items | Non-batch-tracked items |
| Delivery Notes | Batch expiry or quality workflows |
| Sales Invoices (with stock update) | Purchase or receipt workflows |
| Stock Entries (Material Issue, Transfer) | Manufacturing or production orders |

---

## 5. How to Test

### Prerequisites
- An item with **FIFO** valuation method and batch tracking enabled
- At least two Purchase Receipts for that item with **different rates**

---

### Test 1 — Basic FIFO Rate (Most Important)

**Goal:** Confirm the cost comes from the oldest purchase, not the selected batch.

**Steps:**
1. Create a Purchase Receipt: Item X, Batch A, Qty 10, Rate ₹10. Submit.
2. Create a Purchase Receipt: Item X, Batch B, Qty 10, Rate ₹15. Submit.
3. Create a Delivery Note: Item X, **select Batch B**, Qty 5. Submit.
4. Open the submitted Delivery Note → Stock Ledger → check **Incoming Rate**.

**Expected Result:** Incoming Rate = **₹10** (oldest layer, not Batch B's ₹15)

---

### Test 2 — Layer Exhaustion (Auto Rate Switch)

**Goal:** Confirm the rate automatically switches when the first purchase is fully consumed.

**Steps:**
1. Use the same stock from Test 1 (10 pcs @₹10, 10 pcs @₹15).
2. Create a Delivery Note: Item X, **select Batch B**, Qty **15**. Submit.
3. Check the Stock Ledger Incoming Rate.

**Expected Result:** Incoming Rate = **₹11.67** (weighted average: first 10 units @₹10, next 5 units @₹15)

---

### Test 3 — Batch Traceability Intact

**Goal:** Confirm that the batch selection is still recorded correctly for traceability.

**Steps:**
1. After submitting any Delivery Note from the tests above, open it.
2. Check the **Batch No** field on the item row.

**Expected Result:** The batch selected by the user (e.g. Batch B) is still saved on the document. Only the cost was adjusted — the batch record is unchanged.

---

### Test 4 — Sales Invoice with Stock Update

**Goal:** Confirm the fix also works through Sales Invoices.

**Steps:**
1. Create fresh stock: Purchase Receipt, Batch A, Qty 10, Rate ₹10. Submit.
2. Create fresh stock: Purchase Receipt, Batch B, Qty 10, Rate ₹15. Submit.
3. Create a Sales Invoice with **Update Stock = Yes**: Item X, select Batch B, Qty 5. Submit.
4. Check Stock Ledger → Incoming Rate.

**Expected Result:** Incoming Rate = **₹10**

---

### Test 5 — Stock Entry (Material Issue)

**Goal:** Confirm the fix works through Stock Entries.

**Steps:**
1. Create fresh stock as above.
2. Create a Stock Entry of type **Material Issue**: Item X, select Batch B, Qty 5. Submit.
3. Check Stock Ledger → Incoming Rate.

**Expected Result:** Incoming Rate = **₹10**

---

### Where to Check Results

After submitting any outward document:

1. Open the submitted document
2. Click **Stock Ledger** button (top right)
3. Look at the **Incoming Rate** column for the item

Alternatively, check **Profit and Loss** or **Gross Profit** report — the cost of goods sold figures should reflect FIFO rates.

---

## 6. Important Notes

- This fix applies to **new transactions only**. Existing submitted documents are not affected.
- Historical stock entries can be reprocessed using ERPNext's **Repost Item Valuation** tool if needed (consult your system administrator).
- The fix is active as long as the Purva app is installed and the server is running.
