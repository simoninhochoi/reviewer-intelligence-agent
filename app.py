"""Streamlit Web UI — Reviewer Intelligence Agent

Railway 배포용 웹 인터페이스.
CLI의 핵심 기능을 웹에서 사용할 수 있도록 합니다.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Reviewer Intelligence Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일에서 환경변수 로드

_has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY", ""))
_has_s2_key = bool(os.getenv("S2_API_KEY", ""))

with st.sidebar:
    st.title("🔬 RIA")
    st.caption("Reviewer Intelligence Agent")
    st.divider()

    # 환경변수에 키가 없을 때만 입력창 표시
    if _has_anthropic_key:
        st.success("Anthropic API Key 설정됨", icon="✅")
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            help="Claude API 키를 입력하세요.",
        )
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

    if _has_s2_key:
        st.success("S2 API Key 설정됨", icon="✅")
    else:
        s2_key = st.text_input(
            "Semantic Scholar API Key (선택)",
            type="password",
            help="S2 API 키가 있으면 입력하세요. 없어도 동작합니다.",
        )
        if s2_key:
            os.environ["S2_API_KEY"] = s2_key

    st.divider()
    page = st.radio(
        "메뉴",
        [
            "🏠 홈",
            "👤 리뷰어 프로파일링",
            "📚 문서 업로드 & 검색",
            "🚀 전체 파이프라인",
            "💰 비용 리포트",
        ],
    )

# ──────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────


def render_profile(profile_text: str):
    """프로필 텍스트(JSON 또는 마크다운)를 카드 형태로 시각화"""
    import re

    # JSON 파싱 시도
    profile_data = None
    try:
        profile_data = json.loads(profile_text)
    except (json.JSONDecodeError, TypeError):
        # JSON 코드블록 안에 있는 경우
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", profile_text, re.DOTALL)
        if json_match:
            try:
                profile_data = json.loads(json_match.group(1))
            except (json.JSONDecodeError, TypeError):
                pass

    if profile_data and isinstance(profile_data, dict):
        _render_profile_cards(profile_data)
    else:
        # JSON 파싱 실패 시 마크다운 텍스트를 섹션별로 분리해서 표시
        _render_profile_markdown(profile_text)


def _render_profile_cards(data: dict):
    """JSON 프로필 데이터를 카드 형태로 렌더링"""

    # ── 핵심 이론 프레임워크 ──
    frameworks = data.get("core_theoretical_frameworks", [])
    if frameworks:
        st.markdown("#### 🧠 핵심 이론 프레임워크")
        cols = st.columns(min(len(frameworks), 4))
        for i, fw in enumerate(frameworks):
            with cols[i % len(cols)]:
                st.markdown(
                    f'<div style="background:#e8f4f8; padding:12px; border-radius:8px; '
                    f'border-left:4px solid #2196F3; margin-bottom:8px;">'
                    f'<strong>{fw}</strong></div>',
                    unsafe_allow_html=True,
                )

    # ── 방법론적 입장 ──
    method = data.get("methodological_stance", {})
    if method:
        st.markdown("#### 🔬 방법론적 입장")
        col1, col2 = st.columns(2)
        with col1:
            primary = method.get("primary_methods", [])
            if primary:
                st.markdown("**주요 방법론**")
                for m in primary:
                    st.markdown(f"- {m}")
            epistem = method.get("epistemological_position", "")
            if epistem:
                st.markdown(f"**인식론적 위치**: {epistem}")
        with col2:
            prefs = method.get("data_preferences", [])
            if prefs:
                st.markdown("**데이터 선호**")
                for p in prefs:
                    st.markdown(f"- {p}")

    # ── 핵심 개념 ──
    concepts = data.get("key_concepts", [])
    if concepts:
        st.markdown("#### 💡 핵심 개념")
        tags_html = " ".join(
            f'<span style="background:#fff3e0; padding:6px 14px; border-radius:20px; '
            f'margin:4px; display:inline-block; font-size:0.9em; '
            f'border:1px solid #FFB74D;">{c}</span>'
            for c in concepts
        )
        st.markdown(tags_html, unsafe_allow_html=True)
        st.markdown("")  # 간격

    # ── 지적 네트워크 ──
    network = data.get("intellectual_network", {})
    if network:
        st.markdown("#### 🌐 지적 네트워크")
        col1, col2 = st.columns(2)
        with col1:
            coauthors = network.get("frequent_coauthors", [])
            if coauthors:
                st.markdown("**주요 공저자**")
                for a in coauthors[:8]:
                    st.markdown(f"- 👤 {a}")
        with col2:
            cited = network.get("frequently_cited_scholars", [])
            if cited:
                st.markdown("**자주 인용하는 학자**")
                for s in cited[:8]:
                    st.markdown(f"- 📚 {s}")
        lineage = network.get("intellectual_lineage", "")
        if lineage:
            st.caption(f"💬 학문적 계보: {lineage}")

    # ── 비판 패턴 ──
    critical = data.get("critical_patterns", {})
    if critical:
        st.markdown("#### ⚡ 비판 패턴")
        criticisms = critical.get("common_criticisms", [])
        blind_spots = critical.get("theoretical_blind_spots", [])
        if criticisms:
            for c in criticisms:
                st.markdown(
                    f'<div style="background:#fce4ec; padding:10px; border-radius:6px; '
                    f'border-left:4px solid #e53935; margin-bottom:6px;">'
                    f'⚠️ {c}</div>',
                    unsafe_allow_html=True,
                )
        if blind_spots:
            st.markdown("**이론적 사각지대**")
            for b in blind_spots:
                st.markdown(f"- 🔍 {b}")

    # ── 연구 진화 ──
    evolution = data.get("research_evolution", {})
    if evolution:
        st.markdown("#### 📈 연구 진화")
        periods = [
            ("🌱 초기", evolution.get("early_period", "")),
            ("🌿 중기", evolution.get("middle_period", "")),
            ("🌳 최근", evolution.get("recent_period", "")),
        ]
        for label, desc in periods:
            if desc:
                st.markdown(
                    f'<div style="background:#f3e5f5; padding:10px; border-radius:6px; '
                    f'margin-bottom:6px; border-left:4px solid #9C27B0;">'
                    f'<strong>{label}</strong>: {desc}</div>',
                    unsafe_allow_html=True,
                )

    # ── 예상 리뷰 우려사항 ──
    concerns = data.get("likely_review_concerns", [])
    if concerns:
        st.markdown("#### 🎯 예상 리뷰 우려사항")
        for c in concerns:
            if isinstance(c, dict):
                severity = c.get("severity", "minor")
                color = "#e53935" if severity == "major" else "#FF9800"
                badge = "🔴 Major" if severity == "major" else "🟡 Minor"
                concern_text = c.get("concern", "")
                typical = c.get("typical_comment", "")
                st.markdown(
                    f'<div style="background:#fff; padding:12px; border-radius:8px; '
                    f'border:1px solid #e0e0e0; margin-bottom:8px;">'
                    f'<span style="background:{color}; color:white; padding:2px 8px; '
                    f'border-radius:4px; font-size:0.8em;">{badge}</span> '
                    f'<strong>{concern_text}</strong>'
                    f'{"<br><em style=\"color:#666;\">&quot;" + typical + "&quot;</em>" if typical else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"- {c}")


def _render_profile_markdown(text: str):
    """마크다운 텍스트를 섹션별로 나눠서 expander로 표시"""
    import re
    # 섹션 헤더(##, ###, 숫자.)로 분리
    sections = re.split(r'\n(?=#{1,3}\s|(?:\d+\.)\s)', text.strip())

    if len(sections) <= 1:
        # 분리가 안 되면 그냥 보여주되 코드블록 정리
        cleaned = re.sub(r'```json\s*', '', text)
        cleaned = re.sub(r'```\s*', '', cleaned)
        st.markdown(cleaned)
        return

    for section in sections:
        section = section.strip()
        if not section:
            continue
        # 첫 줄을 제목으로
        lines = section.split('\n', 1)
        title = lines[0].strip('#').strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if body:
            with st.expander(title, expanded=True):
                st.markdown(body)
        else:
            st.markdown(f"**{title}**")


def check_api_key() -> bool:
    """API 키가 설정되어 있는지 확인"""
    import os
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("⚠️ 사이드바에서 Anthropic API Key를 입력하세요.")
        return False
    return True


def save_uploaded_file(uploaded_file) -> str:
    """업로드된 파일을 임시 경로에 저장하고 경로 반환"""
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return tmp.name


# ──────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────


def page_home():
    st.title("🔬 Reviewer Intelligence Agent")
    st.markdown(
        """
        까다로운 학술 리뷰어의 저서·논문을 학습하고,
        리뷰를 시뮬레이션하여 **논문 수정 전략을 자동으로 수립**하는
        멀티 에이전트 시스템입니다.
        """
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(
            "**Step 1 — 프로파일링**\n\n"
            "Semantic Scholar에서 리뷰어의 논문을 수집하고 "
            "학술적 관심사, 방법론, 이론적 성향을 분석합니다."
        )
    with col2:
        st.info(
            "**Step 2-3 — 시뮬레이션**\n\n"
            "원고와 리뷰어 프로필을 교차 분석하여 "
            "예상 리뷰 코멘트를 시뮬레이션합니다."
        )
    with col3:
        st.info(
            "**Step 4-5 — 수정 전략**\n\n"
            "시뮬레이션 결과를 바탕으로 "
            "코멘트별 수정 전략과 텍스트 수정안을 생성합니다."
        )

    st.divider()

    st.subheader("에이전트 아키텍처")
    agents_data = {
        "에이전트": ["Profiler", "Gap Analyzer", "Simulator", "Strategist", "Writer"],
        "역할": [
            "리뷰어 학술 프로필 구축",
            "원고-리뷰어 문헌 갭 분석",
            "리뷰 코멘트 시뮬레이션",
            "코멘트별 수정 전략 수립",
            "학술 텍스트 수정안 작성",
        ],
        "모델": ["Sonnet", "Sonnet", "Opus", "Opus", "Opus"],
    }
    st.table(agents_data)


def page_profile():
    st.title("👤 리뷰어 프로파일링")

    from src.acquisition.paper_store import PaperStore
    paper_store = PaperStore()

    tab_existing, tab_new = st.tabs(["📋 기존 프로필 조회", "➕ 새 프로파일 생성"])

    # ── 기존 프로필 조회 탭 ──
    with tab_existing:
        existing_reviewers = paper_store.all_reviewers()

        if existing_reviewers:
            reviewer_names = [r["name"] for r in existing_reviewers if r.get("name")]
            selected_name = st.selectbox(
                "프로파일링된 리뷰어 선택",
                reviewer_names,
                key="profile_select",
            )
            selected = next(
                (r for r in existing_reviewers if r["name"] == selected_name), None
            )

            if selected:
                # 기본 정보
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("H-Index", selected.get("h_index", "N/A"))
                with col2:
                    affiliations = selected.get("affiliations", "")
                    if affiliations and affiliations.startswith("["):
                        import json
                        try:
                            affiliations = ", ".join(json.loads(affiliations))
                        except Exception:
                            pass
                    st.metric("소속", affiliations or "N/A")
                with col3:
                    papers = paper_store.get_reviewer_papers(selected["reviewer_id"])
                    st.metric("수집된 논문", f"{len(papers)}편")

                st.divider()

                # 프로필 본문
                if selected.get("profile_json"):
                    st.subheader("리뷰어 프로필")
                    render_profile(selected["profile_json"])

                # 논문 목록
                if papers:
                    with st.expander(f"수집된 논문 목록 ({len(papers)}편)", expanded=False):
                        for i, p in enumerate(papers[:30], 1):
                            title = p.get("title", "제목 없음")
                            year = p.get("year", "")
                            citations = p.get("citation_count", 0)
                            st.markdown(
                                f"**{i}.** {title} ({year}) — 인용 {citations}회"
                            )

                # 벡터 DB 통계
                from src.vectordb.chroma_store import ChromaStore
                chroma = ChromaStore()
                stats = chroma.get_stats(selected_name)
                if stats["total_chunks"] > 0:
                    st.info(f"📚 업로드된 문서: {stats['total_chunks']}개 청크 (벡터 DB)")
        else:
            st.info("프로파일링된 리뷰어가 없습니다. '새 프로파일 생성' 탭에서 시작하세요.")

    # ── 새 프로파일 생성 탭 ──
    with tab_new:
        st.markdown("Semantic Scholar에서 리뷰어의 논문을 검색하고 학술적 프로필을 구축합니다.")

        if not check_api_key():
            return

        reviewer_name = st.text_input(
            "리뷰어 이름",
            placeholder="예: Christian Reus-Smit",
        )

        if st.button("프로파일 생성", type="primary", disabled=not reviewer_name):
            with st.spinner("Semantic Scholar 검색 중..."):
                try:
                    from src.pipeline import ReviewerIntelligencePipeline

                    pipeline = ReviewerIntelligencePipeline()
                    result = pipeline._step_profiling(reviewer_name)

                    st.success("프로파일 생성 완료!")

                    # 프로필 표시
                    st.subheader("리뷰어 프로필")
                    render_profile(result["profile"])

                    # 논문 목록
                    papers = result.get("papers", [])
                    if papers:
                        st.subheader(f"수집된 논문 ({len(papers)}편)")
                        for i, p in enumerate(papers[:20], 1):
                            title = p.get("title", "제목 없음")
                            year = p.get("year", "")
                            citations = p.get("citation_count", 0)
                            st.markdown(
                                f"**{i}.** {title} ({year}) — 인용 {citations}회"
                            )

                    st.session_state["profile_result"] = result

                except Exception as e:
                    st.error(f"오류 발생: {e}")


def page_pipeline():
    st.title("🚀 전체 파이프라인 실행")
    st.markdown(
        "리뷰어 프로파일링 → 갭 분석 → 리뷰 시뮬레이션 → 수정 전략 → 텍스트 수정"
    )

    if not check_api_key():
        return

    col1, col2 = st.columns(2)

    with col1:
        reviewer_name = st.text_input(
            "리뷰어 이름",
            placeholder="예: Christian Reus-Smit",
            key="pipeline_reviewer",
        )
        mode = st.selectbox(
            "운영 모드",
            ["pre_submission", "post_review"],
            format_func=lambda x: {
                "pre_submission": "투고 전 원고 강화",
                "post_review": "R&R 대응 (실제 리뷰 기반)",
            }[x],
        )

    with col2:
        uploaded_ms = st.file_uploader(
            "원고 파일",
            type=["pdf", "docx", "txt"],
            help="PDF, DOCX, 또는 TXT 형식",
        )
        author_intent = st.text_area(
            "저자의 양보 불가 사항 (선택)",
            placeholder="예: 사회구성주의 프레임워크는 반드시 유지",
            height=100,
        )

    # post_review 모드일 때 리뷰 코멘트 입력
    actual_review = None
    if mode == "post_review":
        review_input = st.text_area(
            "실제 리뷰 코멘트",
            height=200,
            placeholder="리뷰어의 실제 코멘트를 붙여넣으세요...",
        )
        if review_input:
            actual_review = review_input

    can_run = reviewer_name and uploaded_ms
    if mode == "post_review" and not actual_review:
        can_run = False

    if st.button("파이프라인 실행", type="primary", disabled=not can_run):
        # 업로드된 파일 저장
        ms_path = save_uploaded_file(uploaded_ms)

        # 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            from src.pipeline import ReviewerIntelligencePipeline

            pipeline = ReviewerIntelligencePipeline()

            # Step 1: 프로파일링
            status_text.text("Step 1/5: 리뷰어 프로파일링...")
            progress_bar.progress(10)
            profile_result = pipeline._step_profiling(reviewer_name)

            # Step 2: 원고 로드 + 갭 분석
            status_text.text("Step 2/5: 문헌 갭 분석...")
            progress_bar.progress(30)
            manuscript_text = pipeline._load_manuscript(ms_path)
            from src.utils.reference_extractor import extract_references
            manuscript_refs = extract_references(ms_path)
            gap_result = pipeline._step_gap_analysis(
                profile_result["profile"],
                profile_result["papers"],
                manuscript_refs,
            )

            # Step 3: 리뷰 시뮬레이션
            status_text.text("Step 3/5: 리뷰 시뮬레이션...")
            progress_bar.progress(50)
            if mode == "post_review" and actual_review:
                review_result = {
                    "full_review": actual_review,
                    "section_count": 1,
                }
            else:
                review_result = pipeline._step_simulation(
                    profile_result["profile"], manuscript_text
                )

            # Step 4: 수정 전략
            status_text.text("Step 4/5: 수정 전략 수립...")
            progress_bar.progress(70)
            strategy_result = pipeline.strategist.run(
                reviewer_profile=profile_result["profile"],
                simulated_review=review_result["full_review"],
                manuscript_text=manuscript_text,
                author_intent=author_intent,
            )

            # Step 5: 텍스트 수정
            status_text.text("Step 5/5: 텍스트 수정안 생성...")
            progress_bar.progress(90)
            revisions = pipeline._step_revisions(
                profile_result["profile"],
                strategy_result,
                manuscript_text,
            )

            progress_bar.progress(100)
            status_text.text("완료!")

            from src.optimization.cost_tracker import CostTracker
            cost_summary = CostTracker.get_summary()

            # ── 결과 표시 ──
            st.success(
                f"파이프라인 완료! 총 비용: ${cost_summary.get('total_cost', 0):.4f}"
            )

            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "👤 프로필",
                "🔍 갭 분석",
                "📝 시뮬레이션",
                "🎯 수정 전략",
                "✏️ 수정안",
            ])

            with tab1:
                st.markdown(profile_result["profile"])

            with tab2:
                gap_text = gap_result.get("analysis", gap_result.get("raw_response", str(gap_result)))
                st.markdown(gap_text)

            with tab3:
                st.markdown(review_result["full_review"])

            with tab4:
                strat_text = strategy_result.get("strategy", strategy_result.get("raw_response", str(strategy_result)))
                st.markdown(strat_text)

            with tab5:
                rev_text = revisions.get("revision", revisions.get("status", str(revisions)))
                st.markdown(rev_text)

            # JSON 다운로드
            all_results = {
                "profile": profile_result,
                "gap_analysis": gap_result,
                "simulated_review": review_result,
                "strategy": strategy_result,
                "revisions": revisions,
                "cost_summary": cost_summary,
            }
            st.download_button(
                "📥 전체 결과 JSON 다운로드",
                data=json.dumps(all_results, indent=2, default=str, ensure_ascii=False),
                file_name=f"ria_{reviewer_name.replace(' ', '_')}_results.json",
                mime="application/json",
            )

        except Exception as e:
            st.error(f"파이프라인 실행 중 오류: {e}")
            import traceback
            st.code(traceback.format_exc())


def page_cost():
    st.title("💰 비용 리포트")

    try:
        from src.optimization.cost_tracker import CostTracker
        summary = CostTracker.get_summary()
    except Exception:
        summary = {"total_cost": 0, "total_calls": 0}

    col1, col2 = st.columns(2)
    with col1:
        st.metric("총 비용", f"${summary.get('total_cost', 0):.4f}")
    with col2:
        st.metric("총 API 호출", f"{summary.get('total_calls', 0)}회")

    if summary.get("by_agent"):
        st.subheader("에이전트별 비용")
        agent_data = {
            "에이전트": list(summary["by_agent"].keys()),
            "비용 (USD)": [f"${v:.4f}" for v in summary["by_agent"].values()],
        }
        st.table(agent_data)

    if summary.get("by_model"):
        st.subheader("모델별 비용")
        model_data = {
            "모델": list(summary["by_model"].keys()),
            "비용 (USD)": [f"${v:.4f}" for v in summary["by_model"].values()],
        }
        st.table(model_data)

    if st.button("비용 로그 초기화", type="secondary"):
        from src.optimization.cost_tracker import CostTracker
        CostTracker.reset()
        st.success("비용 로그가 초기화되었습니다.")
        st.rerun()


def page_documents():
    st.title("📚 문서 업로드 & 검색")
    st.markdown(
        "리뷰어의 저서·논문을 직접 업로드하여 벡터 DB에 저장하고, "
        "시맨틱 검색으로 관련 내용을 찾습니다."
    )

    tab_upload, tab_search, tab_manage = st.tabs([
        "📤 문서 업로드",
        "🔍 시맨틱 검색",
        "⚙️ 관리",
    ])

    from src.vectordb.chroma_store import ChromaStore
    from src.acquisition.paper_store import PaperStore

    chroma = ChromaStore()
    paper_store = PaperStore()

    # 프로파일링된 리뷰어 목록 로드
    existing_reviewers = paper_store.all_reviewers()
    reviewer_names = [r["name"] for r in existing_reviewers if r.get("name")]

    # ── 업로드 탭 ──
    with tab_upload:
        if reviewer_names:
            select_mode = st.radio(
                "리뷰어 선택 방식",
                ["기존 리뷰어 선택", "새 리뷰어 직접 입력"],
                horizontal=True,
                key="reviewer_select_mode",
            )
            if select_mode == "기존 리뷰어 선택":
                reviewer_name = st.selectbox(
                    "프로파일링된 리뷰어",
                    reviewer_names,
                    key="doc_reviewer_select",
                )
                # 선택된 리뷰어의 현재 프로필 요약 표시
                selected = next(
                    (r for r in existing_reviewers if r["name"] == reviewer_name), None
                )
                if selected and selected.get("profile_json"):
                    with st.expander("현재 프로필 미리보기", expanded=False):
                        st.markdown(selected["profile_json"][:1000] + "...")
            else:
                reviewer_name = st.text_input(
                    "리뷰어 이름",
                    placeholder="예: Christian Reus-Smit",
                    key="doc_reviewer_new",
                )
        else:
            st.info("프로파일링된 리뷰어가 없습니다. '리뷰어 프로파일링' 메뉴에서 먼저 프로파일을 생성하세요.")
            reviewer_name = st.text_input(
                "리뷰어 이름",
                placeholder="예: Christian Reus-Smit",
                key="doc_reviewer",
            )

        upload_method = st.radio(
            "업로드 방식",
            ["파일 업로드", "텍스트 직접 입력"],
            horizontal=True,
        )

        if upload_method == "파일 업로드":
            uploaded_files = st.file_uploader(
                "논문/저서 파일 (여러 개 가능)",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                help="PDF, DOCX, TXT 형식 지원",
            )

            col1, col2 = st.columns(2)
            with col1:
                doc_title = st.text_input("문서 제목 (선택)", key="doc_title")
            with col2:
                doc_year = st.text_input("출판 연도 (선택)", key="doc_year")

            if st.button("벡터 DB에 저장", type="primary", disabled=not (reviewer_name and uploaded_files)):
                total_chunks = 0
                for uploaded_file in uploaded_files:
                    file_path = save_uploaded_file(uploaded_file)
                    metadata = {"title": doc_title or uploaded_file.name}
                    if doc_year:
                        metadata["year"] = doc_year

                    with st.spinner(f"{uploaded_file.name} 처리 중..."):
                        chunk_count = chroma.add_document(
                            reviewer_name=reviewer_name,
                            file_path=file_path,
                            metadata=metadata,
                        )
                    total_chunks += chunk_count
                    st.success(f"✅ {uploaded_file.name} → {chunk_count}개 청크 저장 완료")

                if total_chunks > 0:
                    stats = chroma.get_stats(reviewer_name)
                    st.info(f"📊 {reviewer_name} 컬렉션: 총 {stats['total_chunks']}개 청크 보유")

        else:  # 텍스트 직접 입력
            text_input = st.text_area(
                "텍스트 입력",
                height=300,
                placeholder="논문 또는 저서의 텍스트를 붙여넣으세요...",
            )
            text_title = st.text_input("문서 제목 (선택)", key="text_title")

            if st.button("벡터 DB에 저장", type="primary", disabled=not (reviewer_name and text_input), key="save_text"):
                metadata = {}
                if text_title:
                    metadata["title"] = text_title

                with st.spinner("텍스트 처리 중..."):
                    chunk_count = chroma.add_text(
                        reviewer_name=reviewer_name,
                        text=text_input,
                        metadata=metadata,
                    )
                st.success(f"✅ {chunk_count}개 청크 저장 완료")

                if chunk_count > 0:
                    stats = chroma.get_stats(reviewer_name)
                    st.info(f"📊 {reviewer_name} 컬렉션: 총 {stats['total_chunks']}개 청크 보유")

    # ── 검색 탭 ──
    with tab_search:
        # 벡터 DB에 문서가 있는 리뷰어 목록
        chroma_reviewers = chroma.list_reviewers()
        if chroma_reviewers:
            search_reviewer = st.selectbox(
                "리뷰어 선택",
                chroma_reviewers,
                key="search_reviewer_select",
            )
        else:
            search_reviewer = st.text_input(
                "리뷰어 이름",
                placeholder="예: Christian Reus-Smit",
                key="search_reviewer",
            )
        search_query = st.text_input(
            "검색 쿼리",
            placeholder="예: constructivism in international relations",
        )
        top_k = st.slider("결과 수", min_value=1, max_value=20, value=5)

        if st.button("검색", type="primary", disabled=not (search_reviewer and search_query)):
            with st.spinner("검색 중..."):
                results = chroma.search(
                    reviewer_name=search_reviewer,
                    query=search_query,
                    top_k=top_k,
                )

            if results:
                st.success(f"{len(results)}개 결과 발견")
                for i, r in enumerate(results, 1):
                    distance = r.get("distance", 0)
                    similarity = max(0, 1 - distance) if distance else 0
                    title = r["metadata"].get("title", "")
                    header = f"**#{i}** — 유사도: {similarity:.2%}"
                    if title:
                        header += f" | {title}"

                    with st.expander(header, expanded=(i <= 3)):
                        st.markdown(r["text"])
                        st.caption(f"메타데이터: {r['metadata']}")
            else:
                st.warning("검색 결과가 없습니다. 먼저 문서를 업로드하세요.")

    # ── 관리 탭 ──
    with tab_manage:
        reviewers = chroma.list_reviewers()

        if reviewers:
            st.subheader(f"등록된 리뷰어 ({len(reviewers)}명)")
            for rev in reviewers:
                stats = chroma.get_stats(rev)
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{rev}**")
                with col2:
                    st.write(f"{stats['total_chunks']}개 청크")
                with col3:
                    if st.button("삭제", key=f"del_{rev}"):
                        chroma.delete_reviewer(rev)
                        st.success(f"{rev} 컬렉션 삭제됨")
                        st.rerun()
        else:
            st.info("등록된 리뷰어가 없습니다. 문서를 업로드하세요.")


# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────

if page == "🏠 홈":
    page_home()
elif page == "👤 리뷰어 프로파일링":
    page_profile()
elif page == "📚 문서 업로드 & 검색":
    page_documents()
elif page == "🚀 전체 파이프라인":
    page_pipeline()
elif page == "💰 비용 리포트":
    page_cost()
