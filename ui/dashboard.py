"""Today view for the Daily Discovery Streamlit application."""

from datetime import date

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.orm import Session

from database.db import SessionLocal, initialize_database
from database.models import Discovery, User
from database.repository import Repository
from providers.base import ProviderUnavailable
from providers.wikipedia_provider import WikipediaProvider
from services.discovery_service import DailyDiscoveryService, GenerationError, load_local_catalog
from services.progress_service import ProgressService
from services.preferences_service import DEFAULT_CATEGORIES, THEME_CATEGORIES, PreferencesService
from services.quiz_service import QuizService
from services.rabbit_hole_service import RabbitHoleService
from services.recommendation_service import RecommendationService
from services.review_service import ReviewService
from services.search_service import SearchService
from services.statistics_service import StatisticsService
from ui.discovery_card import render_discovery_card


def get_daily_discoveries(
    session: Session, discovery_date: date, user: User | None = None
) -> list[Discovery]:
    """Generate or load one complete daily collection."""

    candidates = load_local_catalog()
    if user is not None:
        candidates = PreferencesService().filter_candidates(user, discovery_date, candidates)
    discoveries = DailyDiscoveryService(session, candidates=candidates).generate(discovery_date)
    # Materialize relationship-backed fields while the owning session is open.
    return list(discoveries)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #17212b;
            --muted: #64717d;
            --paper: #f5f2eb;
            --accent: #e4572e;
            --line: #ddd7cc;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        .block-container { max-width: 1180px; padding-top: 3rem; }
        h1, h2, h3 { font-family: Georgia, serif; letter-spacing: 0; }
        h1 { font-size: 3.6rem; line-height: 1; margin-bottom: .35rem; }
        [data-testid="stMetric"] { background: #fffdf9; border: 1px solid var(--line); padding: .8rem 1rem; }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] { color: var(--ink); }
        .discovery-kicker { color: var(--accent); font-size: .72rem; font-weight: 700; letter-spacing: .12em; }
        .discovery-kicker span { color: var(--muted); margin-right: .35rem; }
        div[data-testid="stExpander"] { border-color: var(--line); background: #fffdf9; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> str:
    with st.sidebar:
        st.markdown("## DAILY DISCOVERY")
        st.caption("A small, source-backed reason to stay curious.")
        st.divider()
        return st.radio(
            "Navigate",
            [
                "Today",
                "Search",
                "For You",
                "Settings",
                "Rabbit Hole",
                "Explore",
                "Favorites",
                "Quiz",
                "Review",
                "Progress",
                "Statistics",
                "History",
            ],
            label_visibility="collapsed",
        )


def _mark_today_viewed(
    session: Session, user: User, discoveries: list[Discovery], today: date
):
    repository = Repository(session)
    for discovery in discoveries:
        repository.mark_viewed(user, discovery)
        repository.add_learning_history_once(user, discovery, "viewed")
    snapshot = ProgressService(session).record_view(user, today)
    session.commit()
    return snapshot


def _render_cards(
    session: Session,
    user: User,
    discoveries: list[Discovery],
    *,
    title: str,
) -> None:
    st.markdown(f"## {title}")
    repository = Repository(session)
    for start in range(0, len(discoveries), 2):
        columns = st.columns(2, gap="large")
        for position, (column, discovery) in enumerate(
            zip(columns, discoveries[start : start + 2]), start=start + 1
        ):
            interaction = repository.get_interaction(user, discovery)
            with column:
                changed = render_discovery_card(
                    discovery,
                    position,
                    favorite=bool(interaction and interaction.favorite),
                )
            if changed:
                was_favorite = bool(interaction and interaction.favorite)
                repository.set_favorite(
                    user, discovery, not was_favorite
                )
                if not was_favorite:
                    ProgressService(session).record_favorite(user)
                session.commit()
                st.rerun()


def _render_today(session: Session, user: User, today: date) -> None:
    try:
        discoveries = get_daily_discoveries(session, today, user)
    except GenerationError as error:
        st.error(f"Today's collection could not be prepared: {error}")
        return
    snapshot = _mark_today_viewed(session, user, discoveries, today)
    st.caption("TODAY / SOURCE-BACKED COLLECTION")
    st.title("Daily Discovery")
    st.markdown(
        f"### {today.strftime('%A, %B %-d, %Y')}\n\n"
        "A few useful, strange, and wonderful things to carry into the day."
    )
    st.divider()
    metric_columns = st.columns(5)
    metric_columns[0].metric("Discoveries today", len(discoveries))
    metric_columns[1].metric("Categories", len({item.category.name for item in discoveries}))
    metric_columns[2].metric("Sources attached", sum(item.source is not None for item in discoveries))
    metric_columns[3].metric("Day streak", snapshot.current_streak)
    metric_columns[4].metric("Knowledge XP", snapshot.xp)
    _render_cards(session, user, discoveries, title="Your morning collection")
    st.caption("Every item includes a source so you can keep exploring beyond the card.")


def _render_explore(session: Session, user: User) -> None:
    st.caption("EXPLORE / YOUR LIBRARY")
    st.title("Explore")
    filters = st.columns([1, 1, 1.5])
    repository = Repository(session)
    category = filters[0].selectbox(
        "Category", ["All"] + [item.name for item in repository.list_categories()]
    )
    use_date = filters[1].checkbox("Filter date")
    search = filters[2].text_input("Search", placeholder="Try sky, history, or animals")
    selected_date = filters[1].date_input("Date") if use_date else None
    discoveries = repository.list_discoveries(
        discovery_date=selected_date,
        category_name=None if category == "All" else category,
        search=search or None,
    )
    if not discoveries:
        st.info("No discoveries match those filters yet.")
        return
    _render_cards(session, user, discoveries, title=f"{len(discoveries)} discoveries")


def _render_search(session: Session, user: User) -> None:
    st.caption("SEARCH / FIND SOMETHING YOU REMEMBER")
    st.title("Search discoveries")
    query = st.text_input(
        "Search",
        placeholder="Search titles, topics, sources, or descriptions",
        label_visibility="collapsed",
    )
    filters = st.columns([1, 1, 1])
    repository = Repository(session)
    category = filters[0].selectbox(
        "Category", ["All"] + [item.name for item in repository.list_categories()]
    )
    use_date = filters[1].checkbox("Filter date")
    favorites_only = filters[2].checkbox("Favorites only")
    selected_date = filters[1].date_input("Date") if use_date else None
    results = SearchService(session).search(
        query,
        user=user,
        category_name=None if category == "All" else category,
        discovery_date=selected_date,
        favorites_only=favorites_only,
    )
    if not query.strip():
        st.info("Enter a word, topic, source, or phrase to search your discoveries.")
        return
    if not results:
        st.info("No discoveries match that search.")
        return
    st.markdown(f"## {len(results)} matching discoveries")
    for start in range(0, len(results), 2):
        columns = st.columns(2, gap="large")
        for position, (column, result) in enumerate(
            zip(columns, results[start : start + 2]), start=start + 1
        ):
            with column:
                st.caption(
                    f"{result.category} · {result.date.strftime('%B %-d, %Y')}"
                    + (f" · {result.source_name}" if result.source_name else "")
                )
                interaction = repository.get_interaction(user, result.discovery)
                changed = render_discovery_card(
                    result.discovery,
                    position,
                    favorite=bool(interaction and interaction.favorite),
                )
            if changed:
                was_favorite = bool(interaction and interaction.favorite)
                repository.set_favorite(user, result.discovery, not was_favorite)
                if not was_favorite:
                    ProgressService(session).record_favorite(user)
                session.commit()
                st.rerun()


def _render_rabbit_hole() -> None:
    st.caption("RABBIT HOLE / FOLLOW THE CONNECTIONS")
    st.title("Go down the rabbit hole")
    st.write("Start with a topic and follow only source-linked connections.")
    topic = st.text_input(
        "Starting topic", value=st.query_params.get("topic", "Black holes")
    )
    if not topic.strip():
        st.info("Enter a topic to begin exploring.")
        return
    try:
        graph = RabbitHoleService(WikipediaProvider()).explore(topic, limit=6)
    except ProviderUnavailable as error:
        st.warning(f"Wikipedia could not load this topic right now: {error}")
        return

    nodes = [graph.root, *graph.related]
    labels = [node.title for node in nodes]
    x_values = [0] + [1] * len(graph.related)
    y_values = [0] + list(range(len(graph.related), 0, -1))
    figure = go.Figure()
    for index in range(1, len(nodes)):
        figure.add_trace(
            go.Scatter(
                x=[x_values[0], x_values[index]],
                y=[y_values[0], y_values[index]],
                mode="lines",
                line={"color": "#ddd7cc", "width": 2},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="markers+text",
            text=labels,
            textposition="middle right",
            marker={"size": [28] + [18] * len(graph.related), "color": ["#e4572e"] + ["#3c6e71"] * len(graph.related)},
            hovertext=[node.summary for node in nodes],
            hoverinfo="text",
            showlegend=False,
        )
    )
    figure.update_layout(
        height=360,
        margin={"t": 20, "l": 20, "r": 20, "b": 20},
        xaxis={"visible": False},
        yaxis={"visible": False},
        plot_bgcolor="#fffdf9",
    )
    st.plotly_chart(figure, use_container_width=True)
    st.markdown(f"### {graph.root.title}")
    st.write(graph.root.summary)
    st.markdown(f"[Read source]({graph.root.source_url})")
    if not graph.related:
        st.info("No related topics were returned for this page.")
        return
    selected = st.selectbox(
        "Choose a related topic to continue",
        [node.title for node in graph.related],
    )
    selected_node = next(node for node in graph.related if node.title == selected)
    st.caption(selected_node.summary)
    if st.button("Make this the next rabbit hole", key="rabbit-next"):
        st.query_params["topic"] = selected_node.title
        st.rerun()


def _render_for_you(session: Session, user: User, today: date) -> None:
    st.caption("FOR YOU / A LITTLE MORE OF WHAT YOU LIKE")
    st.title("For You")
    st.write("Recommendations follow your saved and viewed categories, with one gentle detour.")
    recommendations = RecommendationService(session).recommend(user, limit=5)
    if not recommendations:
        st.info("View or favorite a few discoveries first, and recommendations will appear here.")
        return
    repository = Repository(session)
    for start in range(0, len(recommendations), 2):
        columns = st.columns(2, gap="large")
        for position, (column, recommendation) in enumerate(
            zip(columns, recommendations[start : start + 2]), start=start + 1
        ):
            discovery = recommendation.discovery
            repository.mark_viewed(user, discovery)
            repository.add_learning_history_once(user, discovery, "recommended", today)
            with column:
                st.caption(recommendation.reason)
                interaction = repository.get_interaction(user, discovery)
                changed = render_discovery_card(
                    discovery,
                    position,
                    favorite=bool(interaction and interaction.favorite),
                )
            if changed:
                was_favorite = bool(interaction and interaction.favorite)
                repository.set_favorite(user, discovery, not was_favorite)
                if not was_favorite:
                    ProgressService(session).record_favorite(user)
                session.commit()
                st.rerun()
    session.commit()


def _render_settings(session: Session, user: User) -> None:
    st.caption("SETTINGS / SHAPE YOUR DISCOVERY")
    st.title("Settings")
    preferences = PreferencesService()
    snapshot = preferences.snapshot(user)
    with st.form("preferences"):
        theme = st.selectbox(
            "Daily theme",
            list(THEME_CATEGORIES),
            index=list(THEME_CATEGORIES).index(snapshot.theme),
        )
        enabled = st.multiselect(
            "Enabled categories",
            DEFAULT_CATEGORIES,
            default=[
                category
                for category in DEFAULT_CATEGORIES
                if category in snapshot.enabled_categories
            ],
        )
        timezone_name = st.text_input("Timezone", value=user.timezone)
        notifications = st.checkbox(
            "Daily notifications enabled", value=user.daily_notification_enabled
        )
        submitted = st.form_submit_button("Save settings", type="primary")
    if submitted:
        try:
            preferences.set_preferences(
                user, theme=theme, enabled_categories=enabled
            )
        except ValueError as error:
            st.error(str(error))
            return
        user.timezone = timezone_name.strip() or "UTC"
        user.daily_notification_enabled = notifications
        session.commit()
        st.success("Settings saved.")


def _render_favorites(session: Session, user: User) -> None:
    st.caption("FAVORITES / SAVED FOR LATER")
    st.title("Favorites")
    discoveries = Repository(session).list_favorites(user)
    if not discoveries:
        st.info("Favorite a discovery to build your personal collection.")
        return
    _render_cards(session, user, discoveries, title="Your saved discoveries")


def _render_history(session: Session, user: User) -> None:
    st.caption("HISTORY / YOUR LEARNING TRAIL")
    st.title("History")
    history = Repository(session).list_learning_history(user)
    if not history:
        st.info("Your viewed discoveries will appear here.")
        return
    st.metric("Learning moments", len(history))
    for entry in history:
        discovery = entry.discovery
        st.markdown(
            f"**{discovery.title}**  \n{discovery.category.name} · "
            f"{entry.date.strftime('%B %-d, %Y')} · {entry.interaction_type}"
        )
        st.divider()


def _render_progress(session: Session, user: User) -> None:
    st.caption("PROGRESS / KEEP GOING")
    st.title("Your learning progress")
    snapshot = ProgressService(session).snapshot(
        Repository(session).get_or_create_progress(user)
    )
    metrics = st.columns(4)
    metrics[0].metric("Current streak", f"{snapshot.current_streak} days")
    metrics[1].metric("Longest streak", f"{snapshot.longest_streak} days")
    metrics[2].metric("Knowledge XP", snapshot.xp)
    metrics[3].metric("Level", f"{snapshot.level} · {snapshot.level_name}")
    if snapshot.xp_to_next_level:
        st.progress(
            min(1.0, snapshot.xp / (snapshot.xp + snapshot.xp_to_next_level)),
            text=f"{snapshot.xp_to_next_level} XP to the next level",
        )
    attempts = Repository(session).list_quiz_attempts(user)
    st.markdown("## Quiz history")
    if not attempts:
        st.info("Complete the daily quiz to start tracking your scores.")
        return
    for attempt in attempts[:10]:
        st.markdown(
            f"**{attempt.date.strftime('%B %-d, %Y')}** · "
            f"{attempt.score}/{attempt.total_questions} correct"
        )


def _render_review(session: Session, user: User, today: date) -> None:
    st.caption("REVIEW / KEEP IT FRESH")
    st.title("Remembered?")
    service = ReviewService(session)
    service.bootstrap_viewed(user, today)
    session.commit()
    due_reviews = service.due_reviews(user, today)
    if not due_reviews:
        st.success("Nothing is due right now. Come back tomorrow for another review.")
        return
    st.write(f"{len(due_reviews)} discovery review{'s' if len(due_reviews) != 1 else ''} due")
    for review in due_reviews[:5]:
        discovery = review.discovery
        st.markdown(f"### {discovery.title}")
        st.caption(f"{discovery.category.name} · learned {discovery.date.strftime('%B %-d, %Y')}")
        st.write(discovery.content)
        columns = st.columns(2)
        if columns[0].button("Yes, I remembered", key=f"remember-{review.id}"):
            service.record_review(user, discovery, True, today)
            session.commit()
            st.rerun()
        if columns[1].button("Needs review", key=f"again-{review.id}"):
            service.record_review(user, discovery, False, today)
            session.commit()
            st.rerun()
        st.divider()


def _render_statistics(session: Session, user: User) -> None:
    st.caption("STATISTICS / SEE YOUR PATTERNS")
    st.title("Learning statistics")
    snapshot = StatisticsService(session).snapshot(user)
    metrics = st.columns(4)
    metrics[0].metric("Discoveries viewed", snapshot.discoveries_viewed)
    metrics[1].metric("Favorites", snapshot.favorites)
    metrics[2].metric("Quiz questions", snapshot.quiz_questions_answered)
    metrics[3].metric("Quiz accuracy", f"{snapshot.quiz_accuracy:.0%}")

    if snapshot.category_counts:
        st.markdown("## Categories you explore")
        category_figure = px.bar(
            x=list(snapshot.category_counts),
            y=list(snapshot.category_counts.values()),
            labels={"x": "Category", "y": "Viewed discoveries"},
            color=list(snapshot.category_counts),
            color_discrete_sequence=["#e4572e", "#3c6e71", "#f2c14e", "#5c80bc"],
        )
        category_figure.update_layout(showlegend=False, height=320, margin=dict(t=20, l=20, r=20, b=20))
        st.plotly_chart(category_figure, use_container_width=True)
    else:
        st.info("View a few discoveries to see category patterns.")

    chart_columns = st.columns(2)
    with chart_columns[0]:
        st.markdown("## Monthly activity")
        if snapshot.monthly_activity:
            monthly_figure = px.line(
                x=list(snapshot.monthly_activity),
                y=list(snapshot.monthly_activity.values()),
                markers=True,
                labels={"x": "Month", "y": "Learning moments"},
            )
            monthly_figure.update_layout(height=300, margin=dict(t=20, l=20, r=20, b=20))
            st.plotly_chart(monthly_figure, use_container_width=True)
        else:
            st.info("Your monthly learning activity will appear here.")
    with chart_columns[1]:
        st.markdown("## Quiz performance")
        if snapshot.quiz_questions_answered:
            accuracy_figure = px.pie(
                names=["Correct", "Needs practice"],
                values=[
                    snapshot.quiz_accuracy,
                    1 - snapshot.quiz_accuracy,
                ],
                color_discrete_sequence=["#3c6e71", "#e4d9c9"],
                hole=0.62,
            )
            accuracy_figure.update_layout(height=300, margin=dict(t=20, l=20, r=20, b=20))
            st.plotly_chart(accuracy_figure, use_container_width=True)
        else:
            st.info("Complete a quiz to see your accuracy.")


def _render_quiz(session: Session, user: User, today: date) -> None:
    st.caption("QUIZ / REMEMBER WHAT YOU SAW")
    st.title("How much did you remember?")
    discoveries = get_daily_discoveries(session, today, user)
    questions = QuizService(session).get_or_generate(today, discoveries)
    if not questions:
        st.info("Today's collection does not have enough discoveries for a quiz yet.")
        return

    result_key = f"quiz-result-{today.isoformat()}"
    result = st.session_state.get(result_key)
    if result is not None:
        score, results = result
        st.success(f"You scored {score} out of {len(questions)}.")
        for question, correct in zip(questions, results):
            icon = "Correct" if correct else "Review"
            st.markdown(f"**{icon}: {question.question}**")
            st.caption(question.explanation)
        if st.button("Try again", key="quiz-reset"):
            del st.session_state[result_key]
            st.rerun()
        return

    st.write("Choose an answer for each question, then submit when you are ready.")
    with st.form("daily-quiz"):
        answers: dict[int, str] = {}
        for number, question in enumerate(questions, start=1):
            st.markdown(f"**{number}. {question.question}**")
            selected = st.radio(
                "Answer",
                ["A", "B", "C", "D"],
                format_func=lambda letter, item=question: (
                    f"{letter}. {item.options['ABCD'.index(letter)]}"
                ),
                key=f"quiz-answer-{question.id}",
                index=None,
                label_visibility="collapsed",
            )
            if selected is not None:
                answers[question.id] = selected
        submitted = st.form_submit_button("Submit answers", type="primary")

    if submitted:
        if len(answers) != len(questions):
            st.warning("Answer every question before submitting.")
            return
        score, results = QuizService.score_answers(questions, answers)
        Repository(session).create_quiz_attempt(user, today, score, len(questions))
        ProgressService(session).record_quiz(user, score, len(questions))
        session.commit()
        st.session_state[result_key] = (score, results)
        st.rerun()


def render_dashboard() -> None:
    """Render the functional Phase 5 Today dashboard."""

    st.set_page_config(
        page_title="Daily Discovery",
        page_icon="D",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()
    view = _render_sidebar()
    initialize_database()
    today = date.today()

    with SessionLocal() as session:
        user = Repository(session).get_or_create_local_user()
        if view == "Today":
            _render_today(session, user, today)
        elif view == "Search":
            _render_search(session, user)
        elif view == "For You":
            _render_for_you(session, user, today)
        elif view == "Settings":
            _render_settings(session, user)
        elif view == "Rabbit Hole":
            _render_rabbit_hole()
        elif view == "Explore":
            _render_explore(session, user)
        elif view == "Favorites":
            _render_favorites(session, user)
        elif view == "Quiz":
            _render_quiz(session, user, today)
        elif view == "Review":
            _render_review(session, user, today)
        elif view == "Progress":
            _render_progress(session, user)
        elif view == "Statistics":
            _render_statistics(session, user)
        else:
            _render_history(session, user)