from bot.common.clock import date_key
from bot.intel.providers.market import EodRow, EodSummary


def build_post_title() -> str:
    return f"[{date_key()} 장마감 요약]"


def _rows(title: str, rows: list[EodRow], by_turnover: bool = False) -> list[str]:
    lines = [title]
    for row in rows[:5]:
        metric = f"거래대금 {row.turnover_billion_krw:.1f}억" if by_turnover else f"등락률 {row.change_pct:+.2f}%"
        lines.append(f"- {row.symbol} {row.name} | {metric}")
    if len(lines) == 1:
        lines.append("- (데이터 없음)")
    return lines


def build_body(timestamp_text: str, summary: EodSummary) -> str:
    lines = [
        f"{timestamp_text} KST 장마감 리포트",
        f"- 날짜: {summary.date_text}",
        f"- KOSPI: {summary.kospi_change_pct:+.2f}%",
        f"- KOSDAQ: {summary.kosdaq_change_pct:+.2f}%",
        "",
    ]
    lines.extend(_rows("[상승 상위 5]", summary.top_gainers))
    lines.append("")
    lines.extend(_rows("[하락 상위 5]", summary.top_losers))
    lines.append("")
    lines.extend(_rows("[거래대금 상위 5]", summary.top_turnover, by_turnover=True))
    return "\n".join(lines)
