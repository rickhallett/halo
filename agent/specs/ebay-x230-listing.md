Using the open Google Chrome browser and the steer CLI for all GUI interaction:

Phase 1 — Find the original purchase:
1. Navigate the eBay tab to https://www.ebay.co.uk/mye/myebay/purchase
2. Use steer ocr to read the page, find the ThinkPad X230 in the purchase history
3. Click into the original listing to get the full spec details (processor, screen size, storage, OS, condition, what was included, original price paid)
4. Record all specs from the original listing

Phase 2 — Create the resale listing:
1. Navigate to https://www.ebay.co.uk/sell/item
2. Create a new listing using the specs gathered from the original purchase
3. The RAM has been upgraded from whatever the original listing stated to 16GB — update the title and description to reflect this
4. Price at 120 GBP Buy It Now — the 16GB RAM upgrade justifies a premium over standard models
5. Postage: Collection only or buyer pays postage
6. Location: Swanage, Dorset, UK
7. Fill in as many fields as possible using steer type, steer click --on, etc.
8. If eBay asks for photos, skip and note it needs manual attention
9. Do NOT submit the final listing — leave it ready for review

Use steer see, steer ocr --store, and steer click --on throughout. Update the job YAML with progress after each phase.
