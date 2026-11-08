// 功能说明：AI 路线规划页前端交互，负责拦截表单提交、消费 SSE 流并逐步渲染过程/正文/地图。
(function () {
    // 缓存页面关键 DOM 节点，供后续渲染函数复用。
    const form = document.getElementById('planner-form');                       // 规划条件表单
    const submitButton = document.getElementById('planner-submit');             // 提交按钮
    const stepList = document.getElementById('planner-step-list');              // 规划过程时间线容器
    const formErrors = document.getElementById('planner-form-errors');          // 表单校验错误容器
    const errorText = document.getElementById('planner-error-text');            // 运行时错误提示容器
    const finalText = document.getElementById('planner-final-text');            // 最终路线正文容器
    const stopGrid = document.getElementById('planner-stop-grid');              // 站点卡片网格容器
    const mapElement = document.getElementById('planner-map');                  // 高德地图容器
    const historyModal = document.getElementById('planner-history-modal');      // 最近规划弹窗
    const historyList = document.getElementById('planner-history-list');        // 最近规划列表
    const initialFinalPlanElement = document.getElementById('initial-final-plan');  // 已有正文数据岛
    // markdown-it 渲染器（若本地脚本已加载）；用于把路线正文 Markdown 转 HTML。
    const markdownRenderer = window.markdownit ? window.markdownit({
        html: false,      // 禁用原始 HTML，防注入
        linkify: true,    // 自动识别链接
        breaks: true      // 换行符转 <br>
    }) : null;
    let finalMarkdownSource = '';   // 累积流式正文的原始 Markdown 源文

    // 页面没有规划表单（如非规划页）时直接退出。
    if (!form) {
        return;
    }

    // 功能说明：转义文本，安全拼接进 HTML，避免破坏结构或注入。
    function escapeHtml(value) {
        // 空值兜底为空串，再依次替换 5 个 HTML 敏感字符。
        return String(value || '')
            .replace(/&/g, '&amp;')      // & 转 &amp;（必须最先替换）
            .replace(/</g, '&lt;')       // < 转 &lt;
            .replace(/>/g, '&gt;')       // > 转 &gt;
            .replace(/"/g, '&quot;')     // 双引号转 &quot;
            .replace(/'/g, '&#039;');    // 单引号转 &#039;
    }

    // 功能说明：切换“规划中”按钮状态（禁用并改文案），防止重复提交。
    function setPlanningState(isPlanning) {
        // 无按钮元素时跳过。
        if (!submitButton) {
            return;
        }

        submitButton.disabled = isPlanning;                                   // 规划中禁用按钮
        submitButton.textContent = isPlanning ? '规划中...' : '开始规划';       // 同步切换文案
    }

    // 功能说明：新一轮规划开始前清空各展示面板，恢复到待运行状态。
    function resetPlannerPanels() {
        // 清空并隐藏表单错误。
        if (formErrors) {
            formErrors.innerHTML = '';
            formErrors.classList.add('is-hidden');
        }
        // 清空过程时间线。
        if (stepList) {
            stepList.innerHTML = '';
        }
        // 清空并隐藏运行时错误。
        if (errorText) {
            errorText.textContent = '';
            errorText.classList.add('is-hidden');
        }
        // 重置正文区为等待占位并标记空状态。
        if (finalText) {
            finalMarkdownSource = '';
            finalText.textContent = '正在等待 AI 输出路线结果...';
            finalText.classList.add('is-empty');
        }
        // 清空并隐藏站点网格。
        if (stopGrid) {
            stopGrid.innerHTML = '';
            stopGrid.classList.add('is-hidden');
        }
        // 恢复地图占位提示。
        if (mapElement) {
            mapElement.innerHTML = '<div id="planner-map-placeholder" class="planner-map-placeholder-cartoon"><strong>等待路线点位</strong><span>AI 生成景点顺序后会自动标点并连线。</span></div>';
        }
    }

    // 功能说明：把表单校验错误列表渲染成错误提示块。
    function showFormErrors(errors) {
        // 无容器时跳过。
        if (!formErrors) {
            return;
        }

        // 每条错误生成一个提示段落（转义后拼接），并显示错误容器。
        formErrors.innerHTML = (errors || []).map((error) => {
            return `<p class="message-item-cartoon error">${escapeHtml(error)}</p>`;
        }).join('');
        formErrors.classList.remove('is-hidden');
    }

    // 功能说明：展示运行时错误（如依赖缺失、规划失败）文本。
    function showRuntimeError(message) {
        // 无容器时跳过。
        if (!errorText) {
            return;
        }

        // 使用传入消息，缺省用通用失败文案，并显示错误容器。
        errorText.textContent = message || 'AI 路线规划失败，请稍后再试。';
        errorText.classList.remove('is-hidden');
    }

    // 功能说明：向“规划过程”时间线追加一个步骤卡片（标题/描述/状态）。
    function appendStep(step) {
        // 无容器时跳过。
        if (!stepList) {
            return;
        }

        // 序号 = 现有步骤数 + 1；状态缺省为 success。
        const index = stepList.querySelectorAll('.planner-step-cartoon').length + 1;
        const status = step.status || 'success';
        // 拼接步骤卡片 HTML（序号 + 标题 + 描述），字段均做转义。
        const html = [
            `<div class="planner-step-cartoon ${escapeHtml(status)}">`,
            `<span>${index}</span>`,
            '<div>',
            `<strong>${escapeHtml(step.title)}</strong>`,
            `<p>${escapeHtml(step.description)}</p>`,
            '</div>',
            '</div>',
        ].join('');
        stepList.insertAdjacentHTML('beforeend', html);   // 追加到时间线末尾
        stepList.scrollTop = stepList.scrollHeight;       // 滚动到底部展示最新步骤
    }

    // 功能说明：开始输出最终路线正文，重置 Markdown 源文并切换到非空状态。
    function startFinalOutput() {
        // 无正文容器时跳过。
        if (!finalText) {
            return;
        }

        finalMarkdownSource = '';                 // 清空累积源文
        renderMarkdownResult('');                 // 先清空渲染区
        finalText.classList.remove('is-empty');   // 去掉空状态标记
    }

    // 功能说明：把收到的正文增量追加到 Markdown 源文并重新渲染（支持逐块流式显示）。
    function appendFinalOutput(content) {
        // 无正文容器时跳过。
        if (!finalText) {
            return;
        }

        // 若仍处于空状态（未收到 final_start），先初始化输出区。
        if (finalText.classList.contains('is-empty')) {
            startFinalOutput();
        }
        finalMarkdownSource += content || '';             // 累加本块正文
        renderMarkdownResult(finalMarkdownSource);        // 用累积全文重新渲染
        finalText.scrollTop = finalText.scrollHeight;     // 滚动到底部跟随输出
    }

    // 功能说明：用 markdown-it 把路线正文渲染为 HTML；无渲染器时降级为纯文本。
    function renderMarkdownResult(markdownText) {
        // 无正文容器时跳过。
        if (!finalText) {
            return;
        }

        // 空文本直接清空渲染区。
        if (!markdownText) {
            finalText.innerHTML = '';
            return;
        }

        if (markdownRenderer) {
            // 有渲染器：按 Markdown 渲染为 HTML。
            finalText.classList.remove('is-plaintext');
            finalText.innerHTML = markdownRenderer.render(markdownText);
        } else {
            // 无渲染器：降级为纯文本显示。
            finalText.classList.add('is-plaintext');
            finalText.textContent = markdownText;
        }
    }

    // 功能说明：把路线站点渲染成卡片列表（第几天第几站、名称、介绍、坐标）。
    function renderStops(stops) {
        // 无容器或无站点时跳过。
        if (!stopGrid || !stops || !stops.length) {
            return;
        }

        // 逐站生成卡片（转义字段），拼接后写入网格并显示。
        stopGrid.innerHTML = stops.map((stop) => {
            return [
                '<article class="planner-stop-card-cartoon">',
                `<span>第 ${escapeHtml(stop.day_index)} 天 · 第 ${escapeHtml(stop.sequence)} 站</span>`,
                `<h3>${escapeHtml(stop.name)}</h3>`,
                `<p>${escapeHtml(stop.intro)}</p>`,
                `<strong>${escapeHtml(stop.longitude)}, ${escapeHtml(stop.latitude)}</strong>`,
                '</article>',
            ].join('');
        }).join('');
        stopGrid.classList.remove('is-hidden');
    }

    // 功能说明：调用 route_map.js 暴露的全局方法，用站点数据重绘高德地图。
    function renderMap(stops) {
        // 全局渲染函数存在时才调用，缺省数据兜底为空数组。
        if (window.renderPlannerRouteMap) {
            window.renderPlannerRouteMap(stops || []);
        }
    }

    // 功能说明：规划成功后把新记录插入“最近规划”列表并更新地址栏为详情页 URL。
    function addHistoryItem(payload) {
        // 无列表容器或无 plan_id 时跳过。
        if (!historyList || !payload.plan_id) {
            return;
        }

        // 从当前表单读取城市和出行时间用于列表展示文案。
        const formData = new FormData(form);
        const city = formData.get('city') || '';
        const travelTime = formData.get('travel_time') || '';
        // 拼详情页 URL：前缀取表单 data 属性，缺省 /planner/。
        const detailUrl = `${form.dataset.detailPrefix || '/planner/'}${payload.plan_id}/`;
        // 移除“暂无记录”空状态项（若存在）。
        const emptyItem = historyList.querySelector('.empty-comment-cartoon');
        if (emptyItem) {
            emptyItem.remove();
        }
        // 在列表顶部插入新记录链接。
        historyList.insertAdjacentHTML('afterbegin', [
            `<a href="${escapeHtml(detailUrl)}" class="planner-history-item-cartoon">`,
            `<strong>${escapeHtml(city)} · ${escapeHtml(travelTime)}</strong>`,
            '<span>刚刚 · 规划成功</span>',
            '</a>',
        ].join(''));
        // 无刷新更新地址栏到详情页 URL，便于刷新/分享定位到本次结果。
        window.history.replaceState({}, '', detailUrl);
    }

    // 功能说明：SSE 事件总调度，按事件名分发到对应的渲染/状态处理逻辑。
    function handleStreamEvent(eventName, payload) {
        // 表单校验失败：回显错误列表并恢复按钮（不走后续渲染）。
        if (eventName === 'validation_error') {
            showFormErrors(payload.errors || []);
            setPlanningState(false);
            return;
        }
        // 过程步骤：向时间线追加一个步骤卡片。
        if (eventName === 'step') {
            appendStep(payload);
            return;
        }
        // 站点数据：渲染站点卡片并绘制高德地图。
        if (eventName === 'route_stops') {
            renderStops(payload.route_stops || []);
            renderMap(payload.route_stops || []);
            return;
        }
        // 正文开始：重置 Markdown 源文，准备接收逐块输出。
        if (eventName === 'final_start') {
            startFinalOutput();
            return;
        }
        // 正文增量：追加一块路线说明文本并重新渲染。
        if (eventName === 'final_delta') {
            appendFinalOutput(payload.content || '');
            return;
        }
        // 规划完成：若正文一直为空则用 done 数据兜底，再渲染地图、写入历史并恢复按钮。
        if (eventName === 'done') {
            // 流式未推过正文（如末轮才生成）时，用 done 携带的 final_plan 兜底渲染。
            if (payload.final_plan && finalText && !finalMarkdownSource.trim()) {
                finalMarkdownSource = payload.final_plan;
                renderMarkdownResult(finalMarkdownSource);
            }
            renderStops(payload.map_stops || []);   // 用落库后的站点重绘卡片
            renderMap(payload.map_stops || []);     // 重绘地图
            addHistoryItem(payload);                // 写入最近规划
            setPlanningState(false);                // 恢复提交按钮
            return;
        }
        // 运行时错误：展示失败原因并恢复按钮。
        if (eventName === 'error') {
            showRuntimeError(payload.message);
            setPlanningState(false);
        }
    }

    // 功能说明：把一段 SSE 文本（event/data 行）解析为 {eventName, payload} 对象。
    function parseSseBlock(block) {
        const lines = block.split(/\r?\n/);   // 按行切分（兼容 \r\n 与 \n）
        let eventName = 'message';   // SSE 默认事件名
        const dataLines = [];        // 收集 data 行内容

        lines.forEach((line) => {
            // event: 行取事件名（去掉前 6 个字符 "event:"）。
            if (line.startsWith('event:')) {
                eventName = line.slice(6).trim();
            }
            // data: 行取数据负载（去掉前 5 个字符 "data:"），多行数据稍后拼接。
            if (line.startsWith('data:')) {
                dataLines.push(line.slice(5).trimStart());
            }
        });

        // 没有 data 行的块（如纯注释/空块）直接丢弃。
        if (!dataLines.length) {
            return null;
        }

        // data 体是后端 json.dumps 的 JSON，解析为对象；多行 data 用换行拼回。
        return {
            eventName: eventName,
            payload: JSON.parse(dataLines.join('\n'))
        };
    }

    // 功能说明：用 ReadableStream 逐块读取 SSE 响应，按空行切分消息并交给事件处理。
    async function readPlannerStream(response) {
        const reader = response.body.getReader();   // response.body 是 ReadableStream
        const decoder = new TextDecoder('utf-8');   // 字节流解码为文本
        let buffer = '';                            // 跨块缓冲，存放尚未完整的消息片段

        while (true) {
            // 逐块读取；result.done 为 true 表示流已结束。
            const result = await reader.read();
            buffer += decoder.decode(result.value || new Uint8Array(), {stream: !result.done});
            // SSE 以空行(\n\n)分隔完整消息；末尾不完整片段留在 buffer 供下一轮拼接。
            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() || '';
            // 对每个完整块解析并分发事件。
            blocks.forEach((block) => {
                const parsed = parseSseBlock(block);
                if (parsed) {
                    handleStreamEvent(parsed.eventName, parsed.payload);
                }
            });
            // 流已结束则退出读取循环。
            if (result.done) {
                break;
            }
        }
    }

    // 功能说明：拦截表单提交，改用 fetch 请求流式接口；能力不足时放行原生提交降级为同步模式。
    async function submitPlannerForm(event) {
        // 浏览器不支持流式读取 或 表单未配置 streamUrl 时，不拦截，走原生提交（同步模式）。
        if (!window.ReadableStream || !form.dataset.streamUrl) {
            return;
        }

        // 阻止表单原生提交，改由 fetch 发起 SSE 流式请求。
        event.preventDefault();
        resetPlannerPanels();          // 清空上一轮结果面板
        setPlanningState(true);        // 进入“规划中”状态

        try {
            // POST 表单数据到流式接口；streamUrl 由模板 data 属性提供。
            const response = await fetch(form.dataset.streamUrl, {
                method: 'POST',
                body: new FormData(form),                 // 以表单数据为请求体
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'  // 标识为 AJAX 请求
                }
            });
            // 响应异常或无可读流时抛错，交由 catch 统一提示。
            if (!response.ok || !response.body) {
                throw new Error('服务端没有返回可读取的流式响应。');
            }
            await readPlannerStream(response);            // 逐块消费 SSE 流
        } catch (error) {
            showRuntimeError(error.message);              // 展示错误原因
            setPlanningState(false);                      // 恢复提交按钮
        }
    }

    // 功能说明：绑定“最近规划”弹窗的打开/关闭按钮点击事件。
    function bindHistoryModal() {
        // 打开按钮：显示弹窗。
        document.querySelectorAll('[data-history-open]').forEach((button) => {
            button.addEventListener('click', function () {
                historyModal.hidden = false;
            });
        });
        // 关闭按钮：隐藏弹窗。
        document.querySelectorAll('[data-history-close]').forEach((button) => {
            button.addEventListener('click', function () {
                historyModal.hidden = true;
            });
        });
    }

    // 功能说明：详情页/同步模式下读取 initial-final-plan 数据岛，直接渲染已有路线正文。
    function renderInitialMarkdownResult() {
        // 数据岛或正文容器缺失时跳过。
        if (!initialFinalPlanElement || !finalText) {
            return;
        }

        // 数据岛内容是 json_script 输出的 JSON 字符串，解析出正文；空串则不渲染。
        const initialText = JSON.parse(initialFinalPlanElement.textContent || '""');
        if (!initialText) {
            return;
        }

        finalMarkdownSource = initialText;                // 作为累积源文
        finalText.classList.remove('is-empty');           // 去掉空状态
        renderMarkdownResult(finalMarkdownSource);        // 渲染正文
    }

    // 绑定表单提交（走流式拦截）；页面加载即渲染已有正文；存在历史弹窗时绑定其开关。
    form.addEventListener('submit', submitPlannerForm);
    renderInitialMarkdownResult();
    if (historyModal) {
        bindHistoryModal();
    }
})();
