import streamlit as st
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("Zig-Zag Plotly Canvas Dashboard")

# 1. Create a base Plotly figure
fig = go.Figure()

# 2. Set the PNG Background Image
# (Replace the source with your local path, e.g., "my_background.png")
fig.add_layout_image(
    dict(
        source="https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=1200", 
        xref="paper", yref="paper",
        x=0, y=1,
        sizex=1, sizey=1,
        sizing="stretch",
        opacity=0.7,
        layer="below"
    )
)

# 3. Add graphs (traces) and assign them to custom axes
# Top-Left Graph (Mapped to x1, y1)
fig.add_trace(go.Scatter(
    x=[1, 2, 3, 4], y=[4, 1, 2, 5], 
    mode="lines+markers", 
    line=dict(color="cyan", width=3),
    xaxis="x1", yaxis="y1"
))

# Middle-Right Graph (Mapped to x2, y2)
fig.add_trace(go.Bar(
    x=["Q1", "Q2", "Q3", "Q4"], y=[15, 25, 20, 30], 
    marker_color="orange", 
    xaxis="x2", yaxis="y2"
))

# Bottom-Left Graph (Mapped to x3, y3)
fig.add_trace(go.Scatter(
    x=[10, 20, 30, 40], y=[5, 15, 10, 20], 
    fill="tozeroy", 
    line=dict(color="lightgreen"),
    xaxis="x3", yaxis="y3"
))

# 4. Use coordinates (domains from 0.0 to 1.0) to position the axes in a zig-zag
fig.update_layout(
    # Top-Left plot space (X: 5% to 40% width, Y: 70% to 95% height)
    xaxis1=dict(domain=[0.05, 0.40], anchor="y1", title="Metric A"),
    yaxis1=dict(domain=[0.70, 0.95], anchor="x1"),

    # Middle-Right plot space (X: 55% to 90% width, Y: 35% to 60% height)
    xaxis2=dict(domain=[0.55, 0.90], anchor="y2", title="Metric B"),
    yaxis2=dict(domain=[0.35, 0.60], anchor="x2"),

    # Bottom-Left plot space (X: 5% to 40% width, Y: 0% to 25% height)
    xaxis3=dict(domain=[0.05, 0.40], anchor="y3", title="Metric C"),
    yaxis3=dict(domain=[0.00, 0.25], anchor="x3"),

    # Canvas properties
    height=800, 
    showlegend=False,
    plot_bgcolor="rgba(0,0,0,0)",  # Makes the plot background transparent to see the image
    paper_bgcolor="rgba(0,0,0,0)", # Makes the figure background transparent
    margin=dict(l=20, r=20, t=20, b=20)
)

# 5. Render the single "canvas" figure in Streamlit
st.plotly_chart(fig, use_container_width=True)