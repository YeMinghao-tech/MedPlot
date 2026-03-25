"""MedPilot Dashboard - Streamlit multi-page application.

Implements J5: Dashboard基础架构 (Streamlit multi-page navigation).
Implements J6-J11: Various dashboard pages.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="MedPilot Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Main entry point for the dashboard."""
    st.title("🏥 MedPilot Dashboard")
    st.markdown("### 个性化医疗导诊 Agent 监控面板")

    # Sidebar navigation
    st.sidebar.title("导航")
    page = st.sidebar.radio(
        "选择页面",
        [
            "📊 系统总览",
            "📚 知识库浏览器",
            "🧠 记忆查看器",
            "🔍 问诊追踪",
            "📈 知识库质量",
            "📋 审计日志",
            "✅ 评估面板",
        ],
    )

    # Route to selected page
    if page == "📊 系统总览":
        overview_page()
    elif page == "📚 知识库浏览器":
        knowledge_browser_page()
    elif page == "🧠 记忆查看器":
        memory_viewer_page()
    elif page == "🔍 问诊追踪":
        query_traces_page()
    elif page == "📈 知识库质量":
        quality_page()
    elif page == "✅ 评估面板":
        evaluation_panel_page()
    elif page == "📋 审计日志":
        audit_logs_page()


def overview_page():
    """J6: System overview page with component config and stats."""
    st.header("📊 系统总览")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("组件状态", "运行中", delta="正常")

    with col2:
        st.metric("今日问诊", "128", delta="+12")

    with col3:
        st.metric("知识库文档", "1,542", delta="+23")

    st.divider()

    st.subheader("组件配置")
    config_data = {
        "组件": ["RAG Engine", "HIS Client", "LLM", "Embedding"],
        "状态": ["✓ 运行中", "✓ 运行中", "✓ 运行中", "✓ 运行中"],
        "模型": ["BGE-zh", "MockHIS", "Qwen-Max", "text-embedding-3"],
    }
    st.dataframe(pd.DataFrame(config_data), use_container_width=True)

    st.divider()

    st.subheader("最近活动")
    activity_data = {
        "时间": ["10:30", "10:28", "10:25", "10:22"],
        "患者ID": ["P***23", "P***45", "P***78", "P***12"],
        "意图": ["医疗咨询", "挂号预约", "知识查询", "医疗咨询"],
        "状态": ["已完成", "已完成", "已完成", "已完成"],
    }
    st.dataframe(pd.DataFrame(activity_data), use_container_width=True)


def knowledge_browser_page():
    """J7: Knowledge base browser with document list and chunk details."""
    st.header("📚 知识库浏览器")

    st.info("知识库浏览器 - 显示已索引的文档和Chunk详情")

    # Mock data for demonstration
    docs = [
        {"doc_id": "D001", "title": "心脏病学指南", "type": "临床指南", "chunks": 45, "更新时间": "2026-03-24"},
        {"doc_id": "D002", "title": "高血压诊疗规范", "type": "诊疗规范", "chunks": 32, "更新时间": "2026-03-23"},
        {"doc_id": "D003", "title": "糖尿病护理标准", "type": "护理标准", "chunks": 28, "更新时间": "2026-03-22"},
    ]

    st.dataframe(pd.DataFrame(docs), use_container_width=True)

    st.divider()

    st.subheader("Chunk 详情预览")
    selected_doc = st.selectbox("选择文档", [d["title"] for d in docs])

    chunks = [
        {"chunk_id": "C001", "内容": "心脏病是由心脏功能异常引起的疾病...", "来源": "D001"},
        {"chunk_id": "C002", "内容": "高血压的诊断标准为收缩压≥140mmHg...", "来源": "D002"},
    ]
    st.dataframe(pd.DataFrame(chunks), use_container_width=True)


def memory_viewer_page():
    """J8: Memory viewer for patient profiles and visit history."""
    st.header("🧠 记忆查看器")

    st.info("患者记忆查看器 - 显示档案和历史就诊记录（已脱敏）")

    patient_id = st.text_input("输入患者ID", value="demo_patient")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("患者档案")
        profile = {
            "patient_id": "P***ent",
            "name": "张*",
            "age": "45",
            "allergies": ["青霉素"],
            "chronic_conditions": ["高血压"],
        }
        st.json(profile)

    with col2:
        st.subheader("历史就诊")
        history = [
            {"日期": "2026-03-20", "科室": "内科", "诊断": "高血压随访"},
            {"日期": "2026-02-15", "科室": "心内科", "诊断": "冠心病待排"},
        ]
        st.dataframe(pd.DataFrame(history), use_container_width=True)


def query_traces_page():
    """J9: Query traces with history list and waterfall chart."""
    st.header("🔍 问诊追踪")

    st.info("问诊追踪 - 历史列表和耗时瀑布图")

    traces = [
        {"trace_id": "T001", "时间": "10:30:15", "患者": "P***23", "意图": "MEDICAL_CONSULTATION", "耗时": "245ms", "状态": "完成"},
        {"trace_id": "T002", "时间": "10:28:42", "患者": "P***45", "意图": "APPOINTMENT_BOOKING", "耗时": "189ms", "状态": "完成"},
        {"trace_id": "T003", "时间": "10:25:33", "患者": "P***78", "意图": "MEDICAL_KNOWLEDGE", "耗时": "312ms", "状态": "完成"},
    ]

    st.dataframe(pd.DataFrame(traces), use_container_width=True)

    st.divider()

    st.subheader("耗时瀑布图")
    waterfall_data = {
        "阶段": ["意图识别", "状态转移", "Tool路由", "RAG查询", "响应生成"],
        "耗时(ms)": [45, 23, 67, 89, 21],
    }
    st.bar_chart(pd.DataFrame(waterfall_data), x="阶段", y="耗时(ms)")


def quality_page():
    """J10: Knowledge base quality panel with retrieval hit rate."""
    st.header("📈 知识库质量")

    st.info("知识库质量面板 - 检索命中率和Faithfulness趋势")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("今日检索命中率", "94.2%", delta="+2.1%")

    with col2:
        st.metric("平均Faithfulness", "0.91", delta="+0.03")

    st.divider()

    st.subheader("趋势图")
    dates = ["03-19", "03-20", "03-21", "03-22", "03-23", "03-24", "03-25"]
    hit_rates = [91.2, 92.5, 93.1, 92.8, 94.5, 93.9, 94.2]
    st.line_chart(pd.DataFrame({"日期": dates, "命中率": hit_rates}), x="日期", y="命中率")


def evaluation_panel_page():
    """K8: Evaluation panel with metrics trends and historical comparison."""
    st.header("✅ 评估面板")

    st.info("评估面板 - 黄金测试集评估结果和趋势")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Overall Score", "0.87", delta="+0.02")
    with col2:
        st.metric("Pass Rate", "94%", delta="+3%")
    with col3:
        st.metric("Total Test Cases", "45", delta="+5")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("各类别通过率")
        categories = ["medical_knowledge", "symptom_to_dept", "booking", "record_generation"]
        pass_rates = [0.92, 0.95, 0.88, 0.85]
        st.bar_chart(pd.DataFrame({"类别": categories, "通过率": pass_rates}), x="类别", y="通过率")

    with col2:
        st.subheader("评估趋势")
        dates = ["03-19", "03-20", "03-21", "03-22", "03-23", "03-24", "03-25"]
        scores = [0.82, 0.83, 0.85, 0.84, 0.86, 0.85, 0.87]
        st.line_chart(pd.DataFrame({"日期": dates, "得分": scores}), x="日期", y="得分")

    st.divider()

    st.subheader("最新评估结果")
    eval_results = [
        {"Case ID": "kb_001", "Category": "medical_knowledge", "Score": 0.92, "Status": "PASS"},
        {"Case ID": "kb_002", "Category": "medical_knowledge", "Score": 0.88, "Status": "PASS"},
        {"Case ID": "symptom_001", "Category": "symptom_to_dept", "Score": 0.95, "Status": "PASS"},
        {"Case ID": "symptom_002", "Category": "symptom_to_dept", "Score": 0.91, "Status": "PASS"},
        {"Case ID": "booking_001", "Category": "booking", "Score": 0.78, "Status": "FAIL"},
    ]
    st.dataframe(pd.DataFrame(eval_results), use_container_width=True)

    st.divider()

    st.subheader("失败案例详情")
    failed = [r for r in eval_results if r["Status"] == "FAIL"]
    if failed:
        for f in failed:
            with st.expander(f"Case: {f['Case ID']} (Score: {f['Score']})"):
                st.write(f"**Category**: {f['Category']}")
                st.write(f"**Score**: {f['Score']}")
                st.write(f"**Reason**: Low answer relevancy")
                st.write(f"**Suggested Action**: Review question-answer alignment")
    else:
        st.success("所有测试用例均已通过！")


def audit_logs_page():
    """J11: Audit logs with filtering by patient ID and operation type."""
    st.header("📋 审计日志")

    st.info("审计日志 - 操作溯源和患者ID筛选（已脱敏）")

    col1, col2 = st.columns(2)
    with col1:
        patient_filter = st.text_input("患者ID筛选", value="")
    with col2:
        action_filter = st.selectbox("操作类型", ["全部", "PATIENT_LOOKUP", "BOOKING_CREATE", "SESSION_CREATE"])

    logs = [
        {"时间": "10:30:15", "操作": "SESSION_CREATE", "患者": "P***23", "结果": "SUCCESS", "操作人": "system"},
        {"时间": "10:30:18", "操作": "PATIENT_LOOKUP", "患者": "P***23", "结果": "SUCCESS", "操作人": "agent"},
        {"时间": "10:30:22", "操作": "BOOKING_CREATE", "患者": "P***23", "结果": "SUCCESS", "操作人": "agent"},
        {"时间": "09:45:12", "操作": "SESSION_CREATE", "患者": "P***45", "结果": "SUCCESS", "操作人": "system"},
    ]

    df = pd.DataFrame(logs)

    if patient_filter:
        df = df[df["患者"].str.contains(patient_filter, na=False)]
    if action_filter != "全部":
        df = df[df["操作"] == action_filter]

    st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
