#!/usr/bin/env python3
import cmd
import requests
import json
import sys
from typing import List, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich import print as rprint
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.markdown import Markdown
from rich.text import Text

class CrawlerIndexerCLI(cmd.Cmd):
    def __init__(self):
        super().__init__()
        self.master_url = "http://16.171.111.186:8000"  # Master node URL with port
        self.current_crawl_id = None
        self.debug = False
        self.console = Console()
        self.intro = Text()
        self.intro.append("Welcome to the Crawler-Indexer CLI\n", style="bold green")
        self.intro.append("Type ", style="white")
        self.intro.append("help", style="bold blue")
        self.intro.append(" or ", style="white")
        self.intro.append("?", style="bold blue")
        self.intro.append(" to list commands.\n", style="white")
        self.prompt = Text()
        self.prompt.append("(crawler-indexer) ", style="bold cyan")

    def cmdloop(self, intro=None):
        """Override cmdloop to print intro with proper formatting"""
        if intro is None:
            intro = self.intro
        self.console.print(intro)
        return super().cmdloop(intro)

    def get_prompt(self):
        """Override get_prompt to return properly formatted prompt"""
        return str(self.prompt)

    def do_debug(self, arg):
        """Toggle debug mode to show detailed error information.
        Usage: debug"""
        self.debug = not self.debug
        self.console.print(f"Debug mode {'[green]enabled[/green]' if self.debug else '[red]disabled[/red]'}")

    def do_start_crawl(self, arg):
        """Start a new crawl with seed URLs and parameters.
        Usage: start_crawl <url1> [url2 url3 ...]
        Example: start_crawl https://example.com https://example.org"""
        if not arg:
            self.console.print("[red]Error: Please provide at least one seed URL[/red]")
            return

        urls = arg.split()
        
        # Create a panel to show the current configuration
        def show_config(config: Dict):
            table = Table(title="Crawl Configuration", show_header=False)
            table.add_column("Parameter", style="cyan")
            table.add_column("Value", style="green")
            
            for key, value in config.items():
                if isinstance(value, list):
                    value = '\n'.join(value)
                table.add_row(key, str(value))
            
            self.console.print(table)

        # Initialize crawl configuration
        config = {
            "urls": urls,
            "depth": 1,
            "allowed_domains": [],
            "respect_robots": True,
            "max_pages": 100,
            "delay": 1.0
        }

        # Show initial configuration
        self.console.print("\n[bold]Initial Configuration:[/bold]")
        show_config(config)

        # Interactive configuration
        self.console.print("\n[bold]Configure Crawl Parameters[/bold]")
        self.console.print("Press Enter to keep current values or provide new values.\n")

        # Configure depth
        depth = IntPrompt.ask(
            "Crawl depth (1-10)",
            default=config["depth"],
            show_default=True
        )
        config["depth"] = max(1, min(10, depth))

        # Configure allowed domains
        self.console.print("\n[bold]Allowed Domains[/bold]")
        self.console.print("Enter domains to crawl (one per line, empty line to finish):")
        domains = []
        while True:
            domain = Prompt.ask("Domain", default="")
            if not domain:
                break
            domains.append(domain)
        if domains:
            config["allowed_domains"] = domains

        # Configure respect_robots
        config["respect_robots"] = Confirm.ask(
            "Respect robots.txt?",
            default=config["respect_robots"]
        )

        # Configure max_pages
        max_pages = IntPrompt.ask(
            "Maximum pages to crawl",
            default=config["max_pages"],
            show_default=True
        )
        config["max_pages"] = max(1, max_pages)

        # Configure delay
        delay = Prompt.ask(
            "Delay between requests (seconds)",
            default=str(config["delay"]),
            show_default=True
        )
        try:
            config["delay"] = float(delay)
        except ValueError:
            self.console.print("[yellow]Invalid delay value, using default[/yellow]")

        # Show final configuration
        self.console.print("\n[bold]Final Configuration:[/bold]")
        show_config(config)

        # Confirm before starting
        if not Confirm.ask("\nStart crawl with these settings?"):
            self.console.print("[yellow]Crawl cancelled[/yellow]")
            return

        try:
            if self.debug:
                self.console.print(f"Sending request to: {self.master_url}/crawl")
                self.console.print(Syntax(json.dumps(config, indent=2), "json"))

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Starting crawl...", total=None)
                response = requests.post(
                    f"{self.master_url}/crawl",
                    json=config,
                    timeout=30
                )
                progress.update(task, completed=True)
            
            if self.debug:
                self.console.print(f"Response status: {response.status_code}")
                self.console.print(f"Response headers: {dict(response.headers)}")
                try:
                    self.console.print(Syntax(json.dumps(response.json(), indent=2), "json"))
                except:
                    self.console.print(f"Response text: {response.text}")

            response.raise_for_status()
            data = response.json()
            self.current_crawl_id = data.get("job_id")
            self.console.print(Panel(
                f"[green]Crawl started successfully![/green]\n"
                f"Job ID: [bold]{self.current_crawl_id}[/bold]",
                title="Success",
                border_style="green"
            ))
        except requests.exceptions.RequestException as e:
            self.console.print(Panel(
                f"[red]Error starting crawl:[/red] {str(e)}",
                title="Error",
                border_style="red"
            ))
            if self.debug:
                self.console.print(f"Full error details: {repr(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    self.console.print(f"Response status: {e.response.status_code}")
                    self.console.print(f"Response text: {e.response.text}")

    def do_status(self, arg):
        """Check the status of the current crawl.
        Usage: status"""
        if not self.current_crawl_id:
            self.console.print("[yellow]No active crawl. Start a crawl first using 'start_crawl'[/yellow]")
            return

        try:
            if self.debug:
                self.console.print(f"Sending request to: {self.master_url}/job/{self.current_crawl_id}")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Fetching status...", total=None)
                response = requests.get(
                    f"{self.master_url}/job/{self.current_crawl_id}",
                    timeout=10
                )
                progress.update(task, completed=True)
            
            if self.debug:
                self.console.print(f"Response status: {response.status_code}")
                self.console.print(f"Response headers: {dict(response.headers)}")

            response.raise_for_status()
            data = response.json()
            
            # Create a table for the status
            table = Table(title=f"Crawl Status - Job {self.current_crawl_id}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Status", data.get('status', 'unknown'))
            table.add_row("URLs", '\n'.join(data.get('urls', [])))
            table.add_row("Task Count", str(data.get('task_count', 0)))
            table.add_row("Indexed Count", str(data.get('indexed_count', 0)))
            table.add_row("Crawl Status", data.get('crawl_status', 'unknown'))
            table.add_row("Index Status", data.get('index_status', 'unknown'))
            if data.get('submission_time'):
                table.add_row("Submission Time", data.get('submission_time'))
            
            self.console.print(table)
        except requests.exceptions.RequestException as e:
            self.console.print(Panel(
                f"[red]Error getting status:[/red] {str(e)}",
                title="Error",
                border_style="red"
            ))
            if self.debug:
                self.console.print(f"Full error details: {repr(e)}")

    def do_search(self, arg):
        """Search the indexed content.
        Usage: search <query>
        Example: search python programming"""
        if not arg:
            self.console.print("[red]Error: Please provide a search query[/red]")
            return

        # Prompt for search type
        search_type = Prompt.ask(
            "Search type",
            choices=["match", "phrase", "boolean"],
            default="match"
        )

        try:
            if self.debug:
                self.console.print(f"Sending request to: {self.master_url}/search")
                self.console.print(f"Query parameters: {{'query': {arg}, 'search_type': {search_type}}}")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Searching...", total=None)
                response = requests.post(
                    f"{self.master_url}/search",
                    json={"query": arg, "search_type": search_type},
                    timeout=10
                )
                progress.update(task, completed=True)
            
            if self.debug:
                self.console.print(f"Response status: {response.status_code}")
                self.console.print(f"Response headers: {dict(response.headers)}")

            response.raise_for_status()
            results = response.json()
            if not results:
                self.console.print("[yellow]No results found.[/yellow]")
                return

            # Create a table for search results
            table = Table(title=f"Search Results for '{arg}'")
            table.add_column("#", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("URL", style="blue")
            table.add_column("Relevance", style="yellow")
            table.add_column("Snippet", style="white")

            for i, result in enumerate(results, 1):
                table.add_row(
                    str(i),
                    result.get('title', 'No title'),
                    result.get('url', 'N/A'),
                    f"{result.get('score', 0):.2f}",
                    result.get('summary', 'No snippet available')
                )
            
            self.console.print(table)
        except requests.exceptions.RequestException as e:
            self.console.print(Panel(
                f"[red]Error performing search:[/red] {str(e)}",
                title="Error",
                border_style="red"
            ))
            if self.debug:
                self.console.print(f"Full error details: {repr(e)}")

    def do_health(self, arg):
        """Check the health of the system.
        Usage: health"""
        try:
            if self.debug:
                self.console.print(f"Sending request to: {self.master_url}/health")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Checking system health...", total=None)
                response = requests.get(
                    f"{self.master_url}/health",
                    timeout=10
                )
                progress.update(task, completed=True)
            
            if self.debug:
                self.console.print(f"Response status: {response.status_code}")
                self.console.print(f"Response headers: {dict(response.headers)}")

            response.raise_for_status()
            data = response.json()
            
            # Create a table for health status
            table = Table(title="System Health")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            
            table.add_row("Overall Status", data.get('status', 'unknown'))
            table.add_row("Crawl Queue", data.get('crawl_queue', 'unknown'))
            table.add_row("Indexer Queue", data.get('indexer_queue', 'unknown'))
            table.add_row("Elasticsearch", data.get('elasticsearch', 'unknown'))
            
            self.console.print(table)
            
            if data.get('metrics'):
                metrics_table = Table(title="System Metrics")
                metrics_table.add_column("Metric", style="cyan")
                metrics_table.add_column("Value", style="green")
                
                for key, value in data['metrics'].items():
                    metrics_table.add_row(key, str(value))
                
                self.console.print(metrics_table)
        except requests.exceptions.RequestException as e:
            self.console.print(Panel(
                f"[red]Error checking health:[/red] {str(e)}",
                title="Error",
                border_style="red"
            ))
            if self.debug:
                self.console.print(f"Full error details: {repr(e)}")

    def do_exit(self, arg):
        """Exit the CLI.
        Usage: exit"""
        if Confirm.ask("Are you sure you want to exit?"):
            self.console.print("[green]Goodbye![/green]")
            return True
        return False

    def do_EOF(self, arg):
        """Exit the CLI (Ctrl+D).
        Usage: Ctrl+D"""
        self.console.print("\n[green]Goodbye![/green]")
        return True

def main():
    try:
        CrawlerIndexerCLI().cmdloop()
    except KeyboardInterrupt:
        print("\n[green]Goodbye![/green]")
        sys.exit(0)

if __name__ == '__main__':
    main()