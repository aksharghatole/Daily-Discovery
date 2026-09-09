"""Reusable Streamlit rendering for a single discovery."""

import streamlit as st

from database.models import Discovery


def render_discovery_card(
    discovery: Discovery,
    position: int,
    *,
    favorite: bool = False,
) -> bool:
    """Render one compact, source-backed discovery card."""

    with st.container(border=True):
        st.markdown(
            f'<div class="discovery-kicker"><span>{position:02d}</span> '
            f"{discovery.category.name.upper()}</div>",
            unsafe_allow_html=True,
        )
        st.subheader(discovery.title)
        if discovery.subtitle:
            st.caption(discovery.subtitle)
        st.write(discovery.content)
        if discovery.description:
            with st.expander("Go a little deeper"):
                st.write(discovery.description)
        if discovery.source:
            st.markdown(f"[Source: {discovery.source.name}]({discovery.source.url})")
        return st.button(
            "Remove favorite" if favorite else "Favorite",
            key=f"favorite-{discovery.id}",
            type="secondary",
        )