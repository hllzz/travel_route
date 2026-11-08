// 功能说明：攻略发布页的景点选择器，负责搜索景点、添加/移除已选并同步到提交用的隐藏字段。
(() => {
    // 取得选择器根容器；页面不存在时直接退出，避免后续查询报错。
    const picker = document.querySelector('[data-guide-attraction-picker]');
    if (!picker) {
        return;
    }

    // 缓存搜索接口地址（由模板 data 属性提供）。
    const searchUrl = picker.dataset.searchUrl;
    // 缓存关键词输入框。
    const keywordInput = picker.querySelector('[data-attraction-keyword]');
    // 缓存搜索按钮。
    const searchButton = picker.querySelector('[data-attraction-search]');
    // 缓存搜索结果展示面板。
    const resultsPanel = picker.querySelector('[data-attraction-results]');
    // 缓存已选景点列表面板。
    const selectedPanel = picker.querySelector('[data-attraction-selected-list]');
    // 用 Set 记录已选景点 id，实现去重判断。
    const selectedIds = new Set();

    // 功能说明：初始化已选景点 id 集合。
    function syncSelectedIds() {
        // 读取服务端回填的已选景点，把其 id 加入集合，避免重复添加。
        selectedPanel.querySelectorAll('[data-selected-attraction]').forEach((item) => {
            selectedIds.add(String(item.dataset.id));
        });
    }

    // 功能说明：根据是否已有已选景点，切换空状态提示的显隐。
    function updateEmptyState() {
        // 取得空状态提示节点。
        const emptyNode = selectedPanel.querySelector('[data-empty-selected]');
        // 判断当前是否已存在已选景点项。
        const hasSelected = selectedPanel.querySelector('[data-selected-attraction]');
        if (emptyNode) {
            // 有已选项时隐藏空状态，无已选项时显示空状态。
            emptyNode.hidden = Boolean(hasSelected);
        }
    }

    // 功能说明：拼接“城市 · 区域 · 名称”作为景点展示文本。
    function buildLabel(attraction) {
        // 先放入城市名。
        const parts = [attraction.city_name];
        // 有区域则追加区域。
        if (attraction.area) {
            parts.push(attraction.area);
        }
        // 最后追加景点名。
        parts.push(attraction.name);
        // 过滤空值后用中点连接成展示文本。
        return parts.filter(Boolean).join(' · ');
    }

    // 功能说明：转义接口返回文本，避免特殊字符破坏页面结构或注入。
    function escapeHtml(value) {
        // 空值兜底为空串，再依次替换 5 个 HTML 敏感字符。
        return String(value || '')
            .replace(/&/g, '&amp;')      // & 转 &amp;（必须最先替换）
            .replace(/</g, '&lt;')       // < 转 &lt;
            .replace(/>/g, '&gt;')       // > 转 &gt;
            .replace(/"/g, '&quot;')     // 双引号转 &quot;
            .replace(/'/g, '&#39;');     // 单引号转 &#39;
    }

    // 功能说明：把景点加入已选列表，生成展示标签和提交用隐藏 input。
    function addAttraction(attraction) {
        // 统一转成字符串 id；已经添加过的景点不重复创建隐藏字段。
        const attractionId = String(attraction.id);
        if (selectedIds.has(attractionId)) {
            return;
        }

        // 创建已选项容器 div。
        const item = document.createElement('div');
        item.className = 'guide-selected-attraction-cartoon';   // 套用样式类
        item.dataset.selectedAttraction = '1';                  // 标记为已选项，供查询/委托识别
        item.dataset.id = attractionId;                         // 记录景点 id
        item.dataset.label = buildLabel(attraction);            // 记录展示文本
        // 生成转义后的展示文本，防止注入。
        const safeLabel = escapeHtml(buildLabel(attraction));
        // 内部包含：提交用隐藏 input（name=attraction_ids）、展示文本、移除按钮。
        item.innerHTML = `
            <input type="hidden" name="attraction_ids" value="${attractionId}">
            <span>${safeLabel}</span>
            <button type="button" data-remove-attraction>移除</button>
        `;
        selectedPanel.appendChild(item);      // 把新项追加到已选列表
        selectedIds.add(attractionId);        // 加入去重集合
        updateEmptyState();                   // 刷新空状态显隐
    }

    // 功能说明：将搜索接口返回的景点渲染成带“添加”按钮的结果列表。
    function renderResults(attractions) {
        // 无结果时显示空提示并返回。
        if (!attractions.length) {
            resultsPanel.innerHTML = '<p>没有搜索到匹配的景点。</p>';
            return;
        }

        // 逐个景点生成卡片 HTML，拼接后写入结果面板。
        resultsPanel.innerHTML = attractions.map((attraction) => {
            const label = buildLabel(attraction);                       // 展示文本
            const score = Number(attraction.score || 0).toFixed(1);     // 评分保留一位小数
            // 有图片用 img，无图片用名称首字占位；均做转义。
            const imageHtml = attraction.image
                ? `<img src="${escapeHtml(attraction.image)}" alt="${escapeHtml(attraction.name)}">`
                : `<span>${escapeHtml(attraction.name.slice(0, 1))}</span>`;
            // 卡片含封面、名称、标签评分，以及携带景点各字段的“添加”按钮（供事件委托读取）。
            return `
                <article class="guide-attraction-result-cartoon">
                    <div class="guide-attraction-result-cover-cartoon">${imageHtml}</div>
                    <div>
                        <strong>${escapeHtml(attraction.name)}</strong>
                        <p>${escapeHtml(label)} · 评分 ${score}</p>
                    </div>
                    <button
                        type="button"
                        data-add-attraction
                        data-id="${attraction.id}"
                        data-name="${escapeHtml(attraction.name)}"
                        data-city-name="${escapeHtml(attraction.city_name)}"
                        data-area="${escapeHtml(attraction.area || '')}"
                        data-score="${attraction.score || 0}"
                        data-image="${escapeHtml(attraction.image || '')}"
                    >添加</button>
                </article>
            `;
        }).join('');
    }

    // 功能说明：按关键词调用后端搜索接口并渲染结果，空关键词不发起请求。
    async function searchAttractions() {
        // 取输入框关键词并去空白；校验搜索关键词，避免提交空搜索。
        const keyword = keywordInput.value.trim();
        if (!keyword) {
            resultsPanel.innerHTML = '<p>请输入景点名、城市、区域或标签再搜索。</p>';
            keywordInput.focus();       // 聚焦输入框提示用户
            return;
        }

        // 先显示搜索中占位，再调用后端搜索接口。
        resultsPanel.innerHTML = '<p>正在搜索景点...</p>';
        // 关键词经 URL 编码后拼到查询串；same-origin 携带同源 Cookie（登录态）。
        const response = await fetch(`${searchUrl}?keyword=${encodeURIComponent(keyword)}`, {
            credentials: 'same-origin',
        });
        // HTTP 非 2xx 时提示失败并返回。
        if (!response.ok) {
            resultsPanel.innerHTML = '<p>搜索失败，请稍后再试。</p>';
            return;
        }
        // 解析 JSON 并渲染结果列表（无 results 字段时兜底空数组）。
        const data = await response.json();
        renderResults(data.results || []);
    }

    // 绑定搜索按钮点击触发搜索。
    searchButton.addEventListener('click', searchAttractions);
    // 关键词输入框监听回车键，按下即触发搜索。
    keywordInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();     // 阻止回车默认行为（避免提交表单）
            searchAttractions();
        }
    });

    // 使用事件委托处理添加和移除（结果项动态生成，绑定在容器上统一响应）。
    picker.addEventListener('click', (event) => {
        // 命中“添加”按钮时，从其 data 属性组装景点对象并加入已选列表。
        const addButton = event.target.closest('[data-add-attraction]');
        if (addButton) {
            addAttraction({
                id: addButton.dataset.id,
                name: addButton.dataset.name,
                city_name: addButton.dataset.cityName,
                area: addButton.dataset.area,
                score: addButton.dataset.score,
                image: addButton.dataset.image,
            });
            return;
        }

        // 命中“移除”按钮时，找到所属已选项，删 id、移除节点并刷新空状态。
        const removeButton = event.target.closest('[data-remove-attraction]');
        if (removeButton) {
            const item = removeButton.closest('[data-selected-attraction]');
            selectedIds.delete(String(item.dataset.id));    // 从去重集合移除
            item.remove();                                  // 删除 DOM 节点
            updateEmptyState();                             // 刷新空状态显隐
        }
    });

    // 初始化：同步服务端回填的已选 id，并设置初始空状态。
    syncSelectedIds();
    updateEmptyState();
})();
