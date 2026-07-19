"""CLI entry point for Market Swarm."""

import argparse
import json

from .engine import run_simulation, print_results


def main():
    parser = argparse.ArgumentParser(
        description="Market Swarm \u2014 LLM-powered market simulation for products & services"
    )
    subparsers = parser.add_subparsers(dest="command")

    # simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run a product simulation")
    sim_parser.add_argument("--product", "-p", required=True, help="Path to product YAML")
    sim_parser.add_argument("--model", "-m", default="claude-sonnet-4-5", help="LLM model to use")
    sim_parser.add_argument("--output", "-o", help="Save results to JSON file")
    sim_parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    sim_parser.add_argument(
        "--pack", default=None, help="Force an industry pack (overrides product_type in YAML)"
    )

    # list-packs command
    subparsers.add_parser("list-packs", help="List available industry packs")

    args = parser.parse_args()

    if args.command == "simulate":
        try:
            result = run_simulation(
                product_path=args.product,
                model=args.model,
                verbose=not args.quiet,
                pack_override=args.pack,
            )
        except RuntimeError as e:
            parser.exit(status=1, message=f"Error: {e}\n")
        print_results(result)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
            print(f"\n\U0001f4be Results saved to {args.output}")

    elif args.command == "list-packs":
        from .registry import list_packs

        packs = list_packs()
        if not packs:
            print("No industry packs found.")
        else:
            print("Available Industry Packs:\n")
            for pack in packs:
                print(
                    f"  {pack.product_type:15s}  {pack.display_name} (v{pack.version}) \u2014 {len(pack.personas)} personas"
                )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
