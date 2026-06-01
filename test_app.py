import streamlit as st
import math

st.set_page_config(page_title="LYNSUS Test App", layout="wide")

st.title("LYNSUS Flatwork Estimator - Test App")

tab1, tab2, tab3, tab4 = st.tabs([
    "Estimator",
    "Client Quote",
    "Update Prices",
    "Crew Planner"
])

with tab1:
    st.header("Estimator")

    sqft = st.number_input("Total Square Feet", min_value=0.0, value=1000.0)
    thickness = st.selectbox("Thickness (inches)", [4, 6, 8, 12])
    concrete_price = st.number_input("Concrete Price per CY", value=150.0)
    labor_rate = st.number_input("Labor Cost per SQFT", value=2.50)
    overhead_percent = st.number_input("Overhead %", value=10.0)
    profit_percent = st.number_input("Profit %", value=20.0)

    concrete_yards = (sqft * thickness) / 324

    materials_cost = concrete_yards * concrete_price
    labor_cost = sqft * labor_rate

    subtotal = materials_cost + labor_cost
    overhead_cost = subtotal * (overhead_percent / 100)
    profit_amount = (subtotal + overhead_cost) * (profit_percent / 100)

    total_bid = subtotal + overhead_cost + profit_amount

    if sqft > 0:
        price_per_sqft = total_bid / sqft
    else:
        price_per_sqft = 0

    st.session_state["total_sqft"] = sqft
    st.session_state["total_bid"] = total_bid
    st.session_state["materials_cost"] = materials_cost
    st.session_state["labor_budget"] = labor_cost
    st.session_state["labor_cost"] = labor_cost
    st.session_state["overhead_cost"] = overhead_cost
    st.session_state["profit_amount"] = profit_amount
    st.session_state["price_per_sqft"] = price_per_sqft
    st.session_state["concrete_yards"] = concrete_yards
    st.session_state["concrete_price"] = concrete_price

    st.subheader("Results")

    st.write(f"Concrete Yards: {concrete_yards:.2f}")
    st.write(f"Materials Cost: ${materials_cost:,.2f}")
    st.write(f"Labor Cost: ${labor_cost:,.2f}")
    st.write(f"Total Bid: ${total_bid:,.2f}")
    st.write(f"Price per SQFT: ${price_per_sqft:.2f}")

with tab2:
    st.header("Client Quote")

    first_name = st.text_input("Client First Name")
    last_name = st.text_input("Client Last Name")
    address = st.text_input("Project Address")

    st.subheader("Quote")

    st.write(f"Client: {first_name} {last_name}")
    st.write(f"Address: {address}")
    st.write(f"Total SQFT: {st.session_state.get('total_sqft', 0):,.2f}")
    st.write(f"Project Total: ${st.session_state.get('total_bid', 0):,.2f}")
    st.write(f"Price per SQFT: ${st.session_state.get('price_per_sqft', 0):.2f}")

with tab3:
    st.header("Update Prices")

    new_price = st.number_input(
        "Concrete Price",
        value=st.session_state.get("concrete_price", 150.0)
    )

    if st.button("Save Price"):
        st.session_state["concrete_price"] = new_price
        st.success("Price Updated")

with tab4:
    st.header("Crew Planner")

    total_sqft = st.session_state.get("total_sqft", 0)
    labor_budget = st.session_state.get("labor_budget", 0)

    production_rate = st.number_input(
        "Production Rate (SQFT/Day)",
        value=500.0
    )

    worker1_rate = st.number_input(
        "Worker 1 Daily Pay",
        value=200.0
    )

    worker2_rate = st.number_input(
        "Worker 2 Daily Pay",
        value=200.0
    )

    daily_crew_cost = worker1_rate + worker2_rate

    if production_rate > 0:
        days_required = math.ceil(total_sqft / production_rate)
    else:
        days_required = 0

    actual_labor_cost = daily_crew_cost * days_required
    variance = labor_budget - actual_labor_cost

    st.write(f"Days Required: {days_required}")
    st.write(f"Daily Crew Cost: ${daily_crew_cost:,.2f}")
    st.write(f"Labor Budget: ${labor_budget:,.2f}")
    st.write(f"Actual Labor Cost: ${actual_labor_cost:,.2f}")
    st.write(f"Variance: ${variance:,.2f}")

    if variance >= 0:
        st.success("Within Budget")
    else:
        st.error("Over Budget")
        