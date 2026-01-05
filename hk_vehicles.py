#!/usr/bin/env python3
"""
Hong Kong First Registered Vehicles Analysis Tool

Fetches and analyzes vehicle registration data from the Hong Kong Transport Department.
Data source: https://data.gov.hk/en-data/dataset/hk-td-wcms_11-first-reg-vehicle
"""

import datetime
import io
import sys
from collections import defaultdict

import pandas as pd
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

BASE_URL = "https://www.td.gov.hk/datagovhk_td/first-reg-vehicle/resources/en/particulars_of_first_registered_vehicle_{month}_{year}_eng.csv"


def fetch_data(months_back: int = 12) -> dict:
    """Fetch vehicle registration data for the past N months."""
    now = datetime.datetime.now()
    data_by_month = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching data...", total=months_back)

        for i in range(months_back):
            # Calculate date for i months ago (data is typically 1 month behind)
            target_date = now - datetime.timedelta(days=(i + 1) * 30)
            month = target_date.month
            year = target_date.year

            month_str = datetime.date(year, month, 1).strftime("%b").lower()
            url = BASE_URL.format(month=month_str, year=year)

            progress.update(task, description=f"Fetching {month_str.capitalize()} {year}...")

            try:
                response = requests.get(url, timeout=30)
                if response.ok:
                    # Decode with utf-8-sig to handle BOM
                    content = response.content.decode('utf-8-sig')
                    df = pd.read_csv(io.StringIO(content))
                    # Clean column names (strip whitespace)
                    df.columns = df.columns.str.strip()
                    data_by_month[(month_str, year)] = df
            except requests.RequestException:
                pass

            progress.advance(task)

    return data_by_month


def sort_data_by_date(data_by_month: dict) -> list:
    """Sort data by date, most recent first."""
    return sorted(
        data_by_month.items(),
        key=lambda x: (x[0][1], datetime.datetime.strptime(x[0][0], '%b').month),
        reverse=True
    )


def get_vehicle_count(df: pd.DataFrame, make: str) -> int:
    """Get count of vehicles by make."""
    return df[df['Vehicle Make'] == make].shape[0]


def get_model_breakdown(df: pd.DataFrame, make: str, model_patterns: list = None) -> pd.DataFrame:
    """Get breakdown of vehicle models for a specific make."""
    df_make = df[df['Vehicle Make'] == make].copy()

    if model_patterns:
        df_make['Grouped Model'] = df_make['Vehicle Model'].apply(
            lambda x: next((m for m in model_patterns if m in str(x).upper()), 'Other')
        )
    else:
        df_make['Grouped Model'] = df_make['Vehicle Model']

    return df_make.groupby('Grouped Model').size().reset_index(name='Count').sort_values('Count', ascending=False)


def get_top_makes(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Get top N vehicle makes by registration count."""
    return df.groupby('Vehicle Make').size().reset_index(name='Count').sort_values('Count', ascending=False).head(n)


def get_fuel_type_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Get breakdown by fuel type."""
    return df.groupby('Fuel Type').size().reset_index(name='Count').sort_values('Count', ascending=False)


def get_vehicle_class_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Get breakdown by vehicle class."""
    return df.groupby('Vehicle Class').size().reset_index(name='Count').sort_values('Count', ascending=False)


def display_summary(sorted_data: list):
    """Display summary statistics."""
    if not sorted_data:
        console.print("[red]No data available.[/red]")
        return

    (month_latest, year_latest), df_latest = sorted_data[0]
    df_prev = sorted_data[1][1] if len(sorted_data) > 1 else None

    # Header
    console.print()
    console.print(Panel(
        f"[bold cyan]Hong Kong Vehicle First Registrations[/bold cyan]\n"
        f"[dim]Data for {month_latest.capitalize()} {year_latest}[/dim]",
        box=box.DOUBLE
    ))

    # Total registrations
    total_current = len(df_latest)
    total_prev = len(df_prev) if df_prev is not None else 0
    delta = total_current - total_prev
    delta_str = f"[green]+{delta}[/green]" if delta > 0 else f"[red]{delta}[/red]" if delta < 0 else "0"

    console.print(f"\n[bold]Total Registrations:[/bold] {total_current:,} ({delta_str} vs prev month)")

    # Tesla Statistics
    console.print("\n" + "=" * 50)
    console.print("[bold blue]TESLA Statistics[/bold blue]")
    console.print("=" * 50)

    tesla_count = get_vehicle_count(df_latest, 'TESLA')
    tesla_prev = get_vehicle_count(df_prev, 'TESLA') if df_prev is not None else 0
    tesla_delta = tesla_count - tesla_prev
    delta_str = f"[green]+{tesla_delta}[/green]" if tesla_delta > 0 else f"[red]{tesla_delta}[/red]" if tesla_delta < 0 else "0"

    console.print(f"New Teslas: [bold]{tesla_count}[/bold] ({delta_str} vs prev month)")

    tesla_models = ['MODEL S', 'MODEL 3', 'MODEL X', 'MODEL Y']
    tesla_breakdown = get_model_breakdown(df_latest, 'TESLA', tesla_models)

    if not tesla_breakdown.empty:
        table = Table(title="Tesla Model Breakdown", box=box.SIMPLE)
        table.add_column("Model", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for _, row in tesla_breakdown.iterrows():
            table.add_row(row['Grouped Model'], str(row['Count']))

        console.print(table)

    # BYD Statistics
    console.print("\n" + "=" * 50)
    console.print("[bold green]BYD Statistics[/bold green]")
    console.print("=" * 50)

    byd_count = get_vehicle_count(df_latest, 'BYD')
    byd_prev = get_vehicle_count(df_prev, 'BYD') if df_prev is not None else 0
    byd_delta = byd_count - byd_prev
    delta_str = f"[green]+{byd_delta}[/green]" if byd_delta > 0 else f"[red]{byd_delta}[/red]" if byd_delta < 0 else "0"

    console.print(f"New BYDs: [bold]{byd_count}[/bold] ({delta_str} vs prev month)")

    byd_breakdown = get_model_breakdown(df_latest, 'BYD')

    if not byd_breakdown.empty:
        table = Table(title="BYD Model Breakdown", box=box.SIMPLE)
        table.add_column("Model", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for _, row in byd_breakdown.head(10).iterrows():
            table.add_row(row['Grouped Model'], str(row['Count']))

        console.print(table)

    # Top Makes
    console.print("\n" + "=" * 50)
    console.print("[bold yellow]Top 10 Vehicle Makes[/bold yellow]")
    console.print("=" * 50)

    top_makes = get_top_makes(df_latest, 10)

    table = Table(box=box.SIMPLE)
    table.add_column("Rank", style="dim", justify="right")
    table.add_column("Make", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("% Share", justify="right", style="yellow")

    for idx, (_, row) in enumerate(top_makes.iterrows(), 1):
        pct = (row['Count'] / total_current) * 100
        table.add_row(str(idx), row['Vehicle Make'], str(row['Count']), f"{pct:.1f}%")

    console.print(table)

    # Fuel Type Breakdown
    console.print("\n" + "=" * 50)
    console.print("[bold magenta]Fuel Type Distribution[/bold magenta]")
    console.print("=" * 50)

    fuel_breakdown = get_fuel_type_breakdown(df_latest)

    table = Table(box=box.SIMPLE)
    table.add_column("Fuel Type", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("% Share", justify="right", style="yellow")

    for _, row in fuel_breakdown.iterrows():
        pct = (row['Count'] / total_current) * 100
        table.add_row(row['Fuel Type'], str(row['Count']), f"{pct:.1f}%")

    console.print(table)

    # Vehicle Class Breakdown
    console.print("\n" + "=" * 50)
    console.print("[bold white]Vehicle Class Distribution[/bold white]")
    console.print("=" * 50)

    class_breakdown = get_vehicle_class_breakdown(df_latest)

    table = Table(box=box.SIMPLE)
    table.add_column("Vehicle Class", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("% Share", justify="right", style="yellow")

    for _, row in class_breakdown.iterrows():
        pct = (row['Count'] / total_current) * 100
        table.add_row(row['Vehicle Class'], str(row['Count']), f"{pct:.1f}%")

    console.print(table)


def display_trends(sorted_data: list):
    """Display monthly trends."""
    if len(sorted_data) < 2:
        console.print("[yellow]Not enough data for trend analysis.[/yellow]")
        return

    console.print("\n" + "=" * 50)
    console.print("[bold cyan]Monthly Registration Trends[/bold cyan]")
    console.print("=" * 50)

    table = Table(box=box.SIMPLE)
    table.add_column("Month", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("Tesla", justify="right", style="blue")
    table.add_column("BYD", justify="right", style="green")
    table.add_column("Electric %", justify="right", style="yellow")

    for (month, year), df in sorted_data[:12]:
        total = len(df)
        tesla = get_vehicle_count(df, 'TESLA')
        byd = get_vehicle_count(df, 'BYD')
        electric = len(df[df['Fuel Type'] == 'Electric'])
        ev_pct = (electric / total * 100) if total > 0 else 0

        table.add_row(
            f"{month.capitalize()} {year}",
            str(total),
            str(tesla),
            str(byd),
            f"{ev_pct:.1f}%"
        )

    console.print(table)


def search_make(sorted_data: list, make: str):
    """Search for a specific vehicle make."""
    if not sorted_data:
        console.print("[red]No data available.[/red]")
        return

    (month_latest, year_latest), df_latest = sorted_data[0]

    # Case-insensitive search
    make_upper = make.upper()
    matches = df_latest[df_latest['Vehicle Make'].str.upper().str.contains(make_upper, na=False)]

    if matches.empty:
        console.print(f"[yellow]No vehicles found matching '{make}'[/yellow]")
        return

    # Get unique makes that match
    unique_makes = matches['Vehicle Make'].unique()

    console.print(f"\n[bold]Search results for '{make}' in {month_latest.capitalize()} {year_latest}:[/bold]")

    for matched_make in unique_makes:
        count = get_vehicle_count(df_latest, matched_make)
        console.print(f"\n[cyan]{matched_make}:[/cyan] {count} registrations")

        breakdown = get_model_breakdown(df_latest, matched_make)
        if not breakdown.empty:
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("Model", style="dim")
            table.add_column("Count", justify="right")

            for _, row in breakdown.head(10).iterrows():
                table.add_row(row['Grouped Model'], str(row['Count']))

            console.print(table)


def interactive_mode(data_by_month: dict):
    """Run interactive mode."""
    sorted_data = sort_data_by_date(data_by_month)

    while True:
        console.print("\n[bold]Commands:[/bold]")
        console.print("  [cyan]summary[/cyan]  - Show summary statistics")
        console.print("  [cyan]trends[/cyan]   - Show monthly trends")
        console.print("  [cyan]search[/cyan]   - Search for a vehicle make")
        console.print("  [cyan]export[/cyan]   - Export latest data to CSV")
        console.print("  [cyan]quit[/cyan]     - Exit")

        try:
            cmd = console.input("\n[bold yellow]>[/bold yellow] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if cmd == 'summary':
            display_summary(sorted_data)
        elif cmd == 'trends':
            display_trends(sorted_data)
        elif cmd == 'search':
            make = console.input("Enter vehicle make to search: ").strip()
            search_make(sorted_data, make)
        elif cmd == 'export':
            if sorted_data:
                (month, year), df = sorted_data[0]
                filename = f"hk_vehicles_{month}_{year}.csv"
                df.to_csv(filename, index=False)
                console.print(f"[green]Exported to {filename}[/green]")
            else:
                console.print("[red]No data to export.[/red]")
        elif cmd in ('quit', 'exit', 'q'):
            console.print("[dim]Goodbye![/dim]")
            break
        else:
            console.print("[red]Unknown command. Try 'summary', 'trends', 'search', 'export', or 'quit'.[/red]")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Hong Kong First Registered Vehicles Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Show summary for latest month
  %(prog)s --trends           Show monthly trends
  %(prog)s --search TOYOTA    Search for Toyota vehicles
  %(prog)s --interactive      Run in interactive mode
  %(prog)s --months 6         Fetch only last 6 months of data
        """
    )

    parser.add_argument('--trends', action='store_true', help='Show monthly trends')
    parser.add_argument('--search', type=str, metavar='MAKE', help='Search for a specific vehicle make')
    parser.add_argument('--interactive', '-i', action='store_true', help='Run in interactive mode')
    parser.add_argument('--months', type=int, default=12, help='Number of months to fetch (default: 12)')
    parser.add_argument('--export', type=str, metavar='FILE', help='Export latest data to CSV file')

    args = parser.parse_args()

    # Fetch data
    console.print("[bold]Hong Kong Vehicle Registration Data[/bold]")
    console.print(f"[dim]Source: data.gov.hk - Transport Department[/dim]\n")

    data_by_month = fetch_data(args.months)

    if not data_by_month:
        console.print("[red]Failed to fetch any data. Please check your internet connection.[/red]")
        sys.exit(1)

    sorted_data = sort_data_by_date(data_by_month)

    console.print(f"[green]Fetched data for {len(data_by_month)} months[/green]\n")

    # Handle commands
    if args.interactive:
        interactive_mode(data_by_month)
    elif args.export:
        if sorted_data:
            (month, year), df = sorted_data[0]
            df.to_csv(args.export, index=False)
            console.print(f"[green]Exported {len(df)} records to {args.export}[/green]")
        else:
            console.print("[red]No data to export.[/red]")
    elif args.search:
        search_make(sorted_data, args.search)
    elif args.trends:
        display_trends(sorted_data)
    else:
        display_summary(sorted_data)


if __name__ == '__main__':
    main()
