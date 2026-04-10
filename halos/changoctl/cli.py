"""changoctl CLI — survival inventory and atmospheric personality engine."""

import argparse
import json
import sys

from . import store
from .engine import sustain, text_summary
from halos.common.log import hlog


def cmd_status(args) -> int:
    inventory = store.get_inventory()
    quote_count = store.count_quotes()

    if args.json_out:
        print(json.dumps({
            "inventory": inventory,
            "quote_count": quote_count,
        }, indent=2))
    else:
        print("=== Chango's Cabinet ===")
        for item in inventory:
            stock = item["stock"]
            label = "EMPTY" if stock == 0 else str(stock)
            print(f"  {item['item']}: {label}")
        print(f"\n  quotes: {quote_count}")

    return 0


def cmd_restock(args) -> int:
    try:
        result = store.restock(args.item, quantity=args.quantity)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "restock", {
        "item": args.item, "quantity": args.quantity, "stock": result["stock"],
    })

    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        print(f"Restocked {args.item}: now {result['stock']}")

    return 0


def cmd_consume(args) -> int:
    try:
        result = store.consume(args.item, mood=args.mood)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    from .flavour import random_action
    action = random_action(args.item)

    hlog("changoctl", "info", "consume", {
        "item": args.item, "mood": args.mood, "stock": result["stock"],
        "out_of_stock": result["out_of_stock"],
    })

    if args.json_out:
        print(json.dumps({
            "action": action,
            "stock": result["stock"],
            "out_of_stock": result["out_of_stock"],
            "log_entry": result["log_entry"],
        }, indent=2))
    else:
        print(action)
        if result["out_of_stock"]:
            print(f"\n[{args.item}: EMPTY -- restock]")
        else:
            print(f"\n[{args.item}: {result['stock']} remaining]")

    return 0


def cmd_sustain(args) -> int:
    try:
        result = sustain(args.mood)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "sustain", {
        "item": result["item"], "mood": args.mood, "stock": result["stock"],
        "out_of_stock": result["out_of_stock"],
        "quote_id": result["quote"]["id"] if result["quote"] else None,
    })

    if args.json_out:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result["formatted"])

    return 0


def cmd_quote_add(args) -> int:
    text = " ".join(args.text) if args.text else ""
    if not text:
        print("error: no quote text provided", file=sys.stderr)
        return 1

    try:
        q = store.add_quote(
            text,
            category=args.category,
            source_module=args.source_module,
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "quote_added", {
        "id": q["id"], "category": args.category,
    })

    if args.json_out:
        print(json.dumps(q, indent=2))
    else:
        print(f"Added quote #{q['id']} [{q['category']}]")

    return 0


def cmd_quote_list(args) -> int:
    quotes = store.list_quotes(category=args.category)

    if args.json_out:
        print(json.dumps(quotes, indent=2))
    else:
        if not quotes:
            print("No quotes in the archive.")
        else:
            for q in quotes:
                print(f"  #{q['id']} [{q['category']}] \"{q['text']}\"")

    return 0


def cmd_quote_random(args) -> int:
    from .config import MOOD_CATEGORY_MAP

    category = None
    if args.mood:
        category = MOOD_CATEGORY_MAP.get(args.mood)

    q = store.random_quote(category=category)

    if args.json_out:
        print(json.dumps(q, indent=2))
    else:
        if q:
            print(f"\"{q['text']}\"")
            print(f"  -- [{q['category']}]")
        else:
            print("The archive is empty. Feed Chango some lines.")

    return 0


def cmd_history(args) -> int:
    history = store.list_consumption_history(
        item=args.item, days=args.days,
    )

    if args.json_out:
        print(json.dumps(history, indent=2))
    else:
        if not history:
            print("No consumption history.")
        else:
            for h in history:
                ts = h["timestamp"][:16].replace("T", " ")
                mood_str = f" mood:{h['mood']}" if h.get("mood") else ""
                qty_str = f"x{h['quantity']}" if h["quantity"] != 1 else ""
                print(f"  [{ts}] {h['item']}{qty_str}{mood_str}")

    return 0


def cmd_sync(args) -> int:
    try:
        from .graph import sync_all
        result = sync_all()
    except ImportError:
        print("error: neo4j not installed (install with: uv sync --extra graph)",
              file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: sync failed: {e}", file=sys.stderr)
        return 1

    hlog("changoctl", "info", "sync", result)

    if args.json_out:
        print(json.dumps(result, indent=2))
    else:
        print(f"Synced {result.get('consumption_count', 0)} consumption logs "
              f"and {result.get('quote_count', 0)} quotes to Beachhead.")

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="changoctl",
        description="changoctl -- survival inventory and atmospheric personality engine",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_out", help="JSON output"
    )

    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Stock levels and quote count")

    # restock
    p_restock = sub.add_parser("restock", help="Add stock")
    p_restock.add_argument("item", help="Item to restock")
    p_restock.add_argument(
        "--quantity", type=int, default=1, help="Quantity to add (default: 1)"
    )

    # consume
    p_consume = sub.add_parser("consume", help="Consume an item")
    p_consume.add_argument("item", help="Item to consume")
    p_consume.add_argument("--mood", default=None, help="Current mood")

    # sustain
    p_sustain = sub.add_parser("sustain", help="Full ritual: mood-aware consume + quote")
    p_sustain.add_argument("--mood", required=True, help="Current mood (required)")

    # quote (subparser group)
    p_quote = sub.add_parser("quote", help="Manage quotes")
    quote_sub = p_quote.add_subparsers(dest="quote_command")

    p_qa = quote_sub.add_parser("add", help="Add a quote")
    p_qa.add_argument("text", nargs="*", help="Quote text")
    p_qa.add_argument("--category", required=True, help="Category")
    p_qa.add_argument("--source-module", default=None, help="Source module")

    p_ql = quote_sub.add_parser("list", help="List quotes")
    p_ql.add_argument("--category", default=None, help="Filter by category")

    p_qr = quote_sub.add_parser("random", help="Random quote")
    p_qr.add_argument("--mood", default=None, help="Filter by mood")

    # history
    p_history = sub.add_parser("history", help="Consumption log")
    p_history.add_argument("--days", type=int, default=None, help="Days to look back")
    p_history.add_argument("--item", default=None, help="Filter by item")

    # sync
    sub.add_parser("sync", help="Replay state to Beachhead (Neo4j)")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    if not hasattr(args, "json_out"):
        args.json_out = False

    dispatch = {
        "status": cmd_status,
        "restock": cmd_restock,
        "consume": cmd_consume,
        "sustain": cmd_sustain,
        "history": cmd_history,
        "sync": cmd_sync,
    }

    if args.command == "quote":
        if not hasattr(args, "quote_command") or not args.quote_command:
            parser.parse_args(["quote", "--help"])
            return 0
        quote_dispatch = {
            "add": cmd_quote_add,
            "list": cmd_quote_list,
            "random": cmd_quote_random,
        }
        return quote_dispatch[args.quote_command](args)

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
