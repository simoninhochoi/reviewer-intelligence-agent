"""CLI 인터페이스 — Reviewer Intelligence Agent

사용법:
    ria run "Christian Reus-Smit" manuscript.docx
    ria profile "Christian Reus-Smit"
    ria cost
    ria upload ./paper.pdf paper123
"""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """Reviewer Intelligence Agent — 학술 리뷰어 대응 도구"""
    pass


@cli.command()
@click.argument("reviewer_name")
@click.argument("manuscript_path")
@click.option(
    "--mode",
    default="pre_submission",
    type=click.Choice(["pre_submission", "post_review"]),
    help="운영 모드",
)
@click.option("--intent", default="", help="저자의 양보 불가 사항")
@click.option("--review", default=None, help="실제 리뷰 코멘트 파일 (post_review 모드)")
def run(reviewer_name: str, manuscript_path: str, mode: str, intent: str, review: str | None):
    """전체 파이프라인 실행

    예시: ria run "Christian Reus-Smit" manuscript.docx
    """
    from src.pipeline import ReviewerIntelligencePipeline

    actual_review = None
    if review:
        actual_review = Path(review).read_text(encoding="utf-8")

    pipeline = ReviewerIntelligencePipeline()
    results = pipeline.run(
        reviewer_name=reviewer_name,
        manuscript_path=manuscript_path,
        mode=mode,
        author_intent=intent,
        actual_review=actual_review,
    )

    console.print("\n[bold green]Pipeline 완료![/bold green]")
    cost = results.get("cost_summary", {})
    console.print(f"총 비용: ${cost.get('total_cost', 0):.4f}")


@cli.command()
@click.argument("reviewer_name")
def profile(reviewer_name: str):
    """리뷰어 프로파일만 실행

    예시: ria profile "Christian Reus-Smit"
    """
    from src.pipeline import ReviewerIntelligencePipeline

    pipeline = ReviewerIntelligencePipeline()
    result = pipeline._step_profiling(reviewer_name)
    console.print(result["profile"])


@cli.command()
def cost():
    """비용 리포트 조회"""
    from src.optimization.cost_tracker import CostTracker

    summary = CostTracker.get_summary()

    console.print(f"\n[bold]API 비용 리포트[/bold]")
    console.print(f"총 비용: [green]${summary['total_cost']:.4f}[/green]")
    console.print(f"총 호출: {summary['total_calls']}회")

    if summary.get("by_agent"):
        table = Table(title="에이전트별 비용")
        table.add_column("에이전트", style="cyan")
        table.add_column("비용 (USD)", justify="right", style="green")
        for agent, agent_cost in summary["by_agent"].items():
            table.add_row(agent, f"${agent_cost:.4f}")
        console.print(table)

    if summary.get("by_model"):
        table = Table(title="모델별 비용")
        table.add_column("모델", style="cyan")
        table.add_column("비용 (USD)", justify="right", style="green")
        for model, model_cost in summary["by_model"].items():
            table.add_row(model, f"${model_cost:.4f}")
        console.print(table)


@cli.command()
@click.argument("pdf_path")
@click.argument("paper_id")
def upload(pdf_path: str, paper_id: str):
    """논문 PDF 수동 업로드

    예시: ria upload ./reus-smit-2018.pdf paper123
    """
    from src.acquisition.manual_upload import ManualUploadHandler

    handler = ManualUploadHandler()
    result = handler.register_upload(paper_id, Path(pdf_path))
    if result:
        console.print(f"[green]업로드 완료: {pdf_path} → {paper_id}[/green]")
    else:
        console.print(f"[red]업로드 실패: 파일을 확인하세요[/red]")


@cli.command()
def reset_cost():
    """비용 로그 초기화"""
    from src.optimization.cost_tracker import CostTracker

    CostTracker.reset()
    console.print("[yellow]비용 로그가 초기화되었습니다.[/yellow]")


if __name__ == "__main__":
    cli()
