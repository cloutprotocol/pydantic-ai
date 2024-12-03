import asyncio
from src.bill_analyzer import BillAnalyzer
from src.bill_parser import parse_bill_url
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

async def analyze_bill_from_url(url: str, test_mode: bool = False, output_dir: str = "analysis_results"):
    """Analyze a congressional bill from its URL
    
    Args:
        url: URL of the bill on congress.gov
        test_mode: If True, only analyze first few important sections
        output_dir: Directory to save analysis results
    """
    console = Console()
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Initialize analyzer with reduced concurrency for test mode
    analyzer = BillAnalyzer(
        model_name="gpt-4",
        max_concurrent_tasks=2 if test_mode else 3,
        cache_results=True
    )
    
    console.print(f"[bold blue]Starting {'test ' if test_mode else ''}analysis of bill:[/] {url}")
    
    # Parse and analyze sections
    sections_processed = 0
    analysis_results = []
    important_sections = set()  # Track sections with funding or key provisions
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        parse_task = progress.add_task("[cyan]Parsing bill sections...", total=None)
        analysis_task = progress.add_task("[green]Analyzing sections...", total=None)
        
        # Queue sections for analysis
        section_count = 0
        async for section in parse_bill_url(url):
            section_count += 1
            sections_processed += 1
            progress.update(parse_task, description=f"[cyan]Parsed {sections_processed} sections")
            
            # In test mode, only analyze:
            # 1. First 3 sections
            # 2. Sections with "appropriation", "funding", or "authorization" in title
            # 3. Maximum of 5 sections total
            if test_mode:
                is_important = any(keyword in section['title'].lower() 
                                 for keyword in ['appropriation', 'funding', 'authorization'])
                if not (section_count <= 3 or (is_important and len(important_sections) < 2)):
                    continue
                if section_count > 5:
                    break
                if is_important:
                    important_sections.add(section['number'])
            
            # Add context about bill structure
            context = {
                "parent_section": section["parent_section"],
                "section_level": section["level"],
                "url": url,
                "test_mode": test_mode
            }
            
            await analyzer.add_section_for_analysis(
                section_text=f"Section {section['number']}. {section['title']}\n\n{section['text']}",
                context=context
            )
        
        # Process analysis queue
        analysis_count = 0
        async for result in analyzer.analyze_sections():
            analysis_count += 1
            progress.update(analysis_task, description=f"[green]Analyzed {analysis_count} sections")
            analysis_results.append(result.model_dump())
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_prefix = "test_" if test_mode else ""
    output_file = output_dir / f"{mode_prefix}bill_analysis_{timestamp}.json"
    
    with output_file.open("w") as f:
        json.dump({
            "url": url,
            "analysis_date": datetime.now().isoformat(),
            "mode": "test" if test_mode else "full",
            "sections_analyzed": len(analysis_results),
            "total_sections": sections_processed,
            "results": analysis_results
        }, f, indent=2)
    
    console.print(f"\n[bold green]Analysis complete![/] Results saved to: {output_file}")
    console.print(f"\nProcessed {len(analysis_results)}/{sections_processed} sections")
    
    # Print summary of key findings
    console.print("\n[bold yellow]Key Findings Summary:[/]")
    total_numeric_funding = 0
    descriptive_funding = []
    
    for result in analysis_results:
        section = result["section"]
        console.print(f"\n[bold]Section {section['number']}:[/] {section['title']}")
        console.print(f"[dim]Summary:[/] {section['summary']}")
        if section.get('funding_amounts'):
            console.print("[dim]Funding:[/]")
            for purpose, amount in section['funding_amounts'].items():
                if isinstance(amount, (int, float)):
                    total_numeric_funding += amount
                    console.print(f"  • {purpose}: ${amount:,.2f}")
                else:
                    descriptive_funding.append(f"  • {purpose}: {amount}")
    
    if total_numeric_funding > 0:
        console.print(f"\n[bold green]Total Quantified Funding:[/] ${total_numeric_funding:,.2f}")
    
    if descriptive_funding:
        console.print("\n[bold yellow]Additional Funding (Non-numeric):[/]")
        for item in descriptive_funding:
            console.print(item)
    
    if test_mode:
        console.print("\n[bold yellow]Note:[/] This was a test analysis of selected sections.")
        console.print("Run without test_mode=True for full analysis.")

if __name__ == "__main__":
    # Example usage with the Inflation Reduction Act
    BILL_URL = "https://www.congress.gov/bill/117th-congress/house-bill/5376/text"
    
    # Run test mode first
    print("Running test analysis...")
    asyncio.run(analyze_bill_from_url(BILL_URL, test_mode=True))
    
    # Ask user if they want to proceed with full analysis
    response = input("\nProceed with full analysis? (y/n): ").lower().strip()
    if response == 'y':
        print("\nRunning full analysis...")
        asyncio.run(analyze_bill_from_url(BILL_URL, test_mode=False)) 