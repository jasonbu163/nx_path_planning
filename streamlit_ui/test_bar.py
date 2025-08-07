import streamlit as st
import random as rd
import time

st.title("Bar Chart")
st.subheader("A simple bar chart")

# 添加特效选择
effect_option = st.radio("选择完成后的特效:", ("气球", "雪花", "两个都有", "都不需要"))
    
# 添加一个按钮来触发进度条
if st.button("开始进度条"):
    progress_bar = st.progress(0, text="Loading...")    
    time.sleep(0.5)

    if effect_option == "气球":
        for i in range(101):
            progress_bar.progress(i, text=f"Loading...{i/100:.2%}")
            time.sleep(rd.randint(1, 5)/100)
        
        st.success("Done")
        st.balloons()

    elif effect_option == "雪花":
        for i in range(101):
            progress_bar.progress(i, text=f"Loading...{i/100:.2%}")
            time.sleep(rd.randint(1, 5)/100)
        
        st.success("Done")
        st.snow()

    elif effect_option == "两个都有":
        for i in range(101):
            progress_bar.progress(i, text=f"Loading...{i/100:.2%}")
            time.sleep(rd.randint(1, 5)/100)
        
        st.success("Done")
        st.balloons()
        st.snow()

    else:
        progress_bar.empty()    
        st.error("请选择一种效果")
    
    # 添加一个清除按钮
    if st.button("清除结果"):
        st.rerun()