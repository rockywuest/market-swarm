"""CLI entry point for Market Swarm."""

import argparse
import json

from .engine import DEFAULT_MODEL, print_results, run_simulation


def main():
    parser = argparse.ArgumentParser(
        description="Market Swarm \u2014 LLM-powered market simulation for products & services"
    )
    subparsers = parser.add_subparsers(dest="command")

    # simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run a product simulation")
    sim_parser.add_argument("--product", "-p", required=True, help="Path to product YAML")
    sim_parser.add_argument(
        "--model", "-m", default=DEFAULT_MODEL, help=f"LLM model to use (default: {DEFAULT_MODEL})"
    )
    sim_parser.add_argument("--output", "-o", help="Save results to JSON file")
    sim_parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    sim_parser.add_argument(
        "--pack", default=None, help="Force an industry pack (overrides product_type in YAML)"
    )
    sim_parser.add_argument(
        "--population",
        default=None,
        help="Load consumer population (format: source:N, e.g. nemotron-usa:200, finepersonas:100, or hf:dataset:column:50)",
    )
    sim_parser.add_argument(
        "--population-seed",
        type=int,
        default=42,
        help="Random seed for population sampling (default: 42)",
    )
    sim_parser.add_argument(
        "--population-only",
        action="store_true",
        help="Use only population personas, skip pack's expert personas",
    )

    # calibrate command
    cal_parser = subparsers.add_parser(
        "calibrate", help="Run persona calibration harness (validate realism)"
    )
    cal_parser.add_argument(
        "--questions", "-q", required=True, help="Path to calibration question set YAML"
    )
    cal_parser.add_argument(
        "--pack", "-p", default="fmcg", help="Industry pack to calibrate (default: fmcg)"
    )
    cal_parser.add_argument(
        "--model", "-m", default=DEFAULT_MODEL, help=f"LLM model to use (default: {DEFAULT_MODEL})"
    )
    cal_parser.add_argument("--output", "-o", help="Save report to JSON file")

    # list-packs command
    subparsers.add_parser("list-packs", help="List available industry packs")

    args = parser.parse_args()

    if args.command == "simulate":
        try:
            extra_personas = None
            if args.population:
                from .population import load_population

                # Parse population argument: "source:N" format
                parts = args.population.rsplit(":", 1)
                if len(parts) != 2:
                    raise ValueError(
                        "Invalid population format. Use: source:N (e.g., nemotron-usa:200)"
                    )
                source, n_str = parts
                try:
                    n = int(n_str)
                except ValueError:
                    raise ValueError(f"Invalid population count: {n_str}")

                extra_personas = load_population(source, n, seed=args.population_seed)

                if args.population_only:
                    # Override pack personas entirely
                    from .registry import get_pack

                    if args.pack:
                        pack = get_pack(args.pack)
                    else:
                        # Need to load product to get product_type
                        import yaml

                        with open(args.product) as f:
                            product_data = yaml.safe_load(f)
                        product_type = product_data.get("product", {}).get("product_type", "fmcg")
                        pack = get_pack(product_type)
                    pack.personas = []

            result = run_simulation(
                product_path=args.product,
                model=args.model,
                verbose=not args.quiet,
                pack_override=args.pack,
                extra_personas=extra_personas,
            )
        except RuntimeError as e:
            parser.exit(status=1, message=f"Error: {e}\n")
        print_results(result)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
            print(f"\n\U0001f4be Results saved to {args.output}")

    elif args.command == "calibrate":
        from .calibration import (
            export_calibration_json,
            load_question_set,
            print_calibration_report,
            run_calibration,
        )

        try:
            questions = load_question_set(args.questions)
            report = run_calibration(
                personas_or_pack=args.pack,
                questions=questions,
                model=args.model,
            )
        except (FileNotFoundError, ValueError) as e:
            parser.exit(status=1, message=f"Error: {e}\n")

        print_calibration_report(report)

        if args.output:
            export_calibration_json(report, args.output)
            print(f"\nReport saved to {args.output}")

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
