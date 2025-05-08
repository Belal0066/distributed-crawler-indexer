import requests
import time
from typing import List, Optional
import json
import argparse
import cmd
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class CrawlClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def submit_crawl(self, urls: List[str], allowed_domains: Optional[List[str]] = None, depth: int = 1) -> str:
        """Submit a new crawl job and return the job ID."""
        response = requests.post(
            f"{self.base_url}/submit_crawl",
            json={
                "urls": urls,
                "allowed_domains": allowed_domains,
                "depth": depth
            }
        )
        response.raise_for_status()
        return response.json()["job_id"]

    def get_job_status(self, job_id: str) -> dict:
        """Get the status of a crawl job."""
        response = requests.get(f"{self.base_url}/job_status/{job_id}")
        response.raise_for_status()
        return response.json()

    def monitor_job(self, job_id: str, interval: int = 5) -> dict:
        """Monitor a job until it's complete."""
        while True:
            status = self.get_job_status(job_id)
            
            # Create status table
            table = Table(title=f"Job Status: {job_id}")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            
            table.add_row("Crawl", status['crawl_status'])
            table.add_row("Index", status['index_status'])
            
            console.print(table)
            
            if status['crawl_status'] in ['SUCCESS', 'FAILURE'] and status['index_status'] in ['completed', 'pending']:
                return status
            
            time.sleep(interval)

    def search(self, query: str) -> dict:
        """Search through crawled content."""
        response = requests.get(
            f"{self.base_url}/search",
            params={"query": query}
        )
        response.raise_for_status()
        return response.json()

class CrawlCLI(cmd.Cmd):
    intro = 'Welcome to the Web Crawler CLI. Type help or ? to list commands.\n'
    prompt = '(crawler) '

    def __init__(self):
        super().__init__()
        self.client = CrawlClient()
        self.current_job_id = None

    def do_crawl(self, arg):
        """Start a new crawl job.
        Usage: crawl <url_file> [--depth DEPTH] [--domains DOMAIN1,DOMAIN2]
        """
        try:
            parser = argparse.ArgumentParser()
            parser.add_argument('url_file', help='File containing URLs to crawl')
            parser.add_argument('--depth', type=int, default=1, help='Crawl depth')
            parser.add_argument('--domains', help='Comma-separated list of allowed domains')
            
            args = parser.parse_args(arg.split())
            
            # Read URLs from file
            with open(args.url_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            # Parse allowed domains
            allowed_domains = args.domains.split(',') if args.domains else None
            
            # Submit crawl job
            console.print("[bold blue]Submitting crawl job...[/bold blue]")
            self.current_job_id = self.client.submit_crawl(
                urls=urls,
                allowed_domains=allowed_domains,
                depth=args.depth
            )
            console.print(f"[green]Job submitted with ID: {self.current_job_id}[/green]")
            
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")

    def do_status(self, arg):
        """Check the status of the current crawl job.
        Usage: status [job_id]
        """
        try:
            job_id = arg.strip() if arg.strip() else self.current_job_id
            if not job_id:
                console.print("[yellow]No job ID provided and no current job[/yellow]")
                return
            
            status = self.client.get_job_status(job_id)
            
            # Create status table
            table = Table(title=f"Job Status: {job_id}")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            
            table.add_row("Crawl", status['crawl_status'])
            table.add_row("Index", status['index_status'])
            
            console.print(table)
            
            if status['result']:
                console.print(Panel(json.dumps(status['result'], indent=2), title="Result"))
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")

    def do_monitor(self, arg):
        """Monitor the current crawl job until completion.
        Usage: monitor [job_id] [--interval SECONDS]
        """
        try:
            parser = argparse.ArgumentParser()
            parser.add_argument('job_id', nargs='?', help='Job ID to monitor')
            parser.add_argument('--interval', type=int, default=5, help='Status check interval in seconds')
            
            args = parser.parse_args(arg.split())
            
            job_id = args.job_id if args.job_id else self.current_job_id
            if not job_id:
                console.print("[yellow]No job ID provided and no current job[/yellow]")
                return
            
            console.print(f"[bold blue]Monitoring job {job_id}...[/bold blue]")
            result = self.client.monitor_job(job_id, args.interval)
            
            if result['crawl_status'] == 'SUCCESS':
                console.print("[green]Crawl completed successfully![/green]")
                if result['result']:
                    console.print(Panel(json.dumps(result['result'], indent=2), title="Result"))
            else:
                console.print("[red]Crawl failed![/red]")
                console.print(f"[red]Error: {result.get('result')}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")

    def do_search(self, arg):
        """Search through crawled content.
        Usage: search "your search query"
        """
        try:
            if not arg:
                console.print("[yellow]Please provide a search query[/yellow]")
                return
            
            results = self.client.search(arg)
            
            if not results['results']:
                console.print("[yellow]No results found[/yellow]")
                return
            
            # Create results table
            table = Table(title=f"Search Results for: {arg}")
            table.add_column("Title", style="cyan")
            table.add_column("URL", style="blue")
            table.add_column("Score", style="green")
            table.add_column("Summary", style="white")
            
            for result in results['results']:
                table.add_row(
                    result['title'],
                    result['url'],
                    f"{result['score']:.2f}",
                    result['summary']
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")

    def do_exit(self, arg):
        """Exit the CLI."""
        console.print("[yellow]Goodbye![/yellow]")
        return True

    def do_EOF(self, arg):
        """Exit on EOF (Ctrl+D)."""
        print()
        return self.do_exit(arg)

def main():
    # Create CLI interface
    cli = CrawlCLI()
    cli.cmdloop()

if __name__ == "__main__":
    main() 