// 功能说明：整体用 IIFE（立即执行函数）封装高德路线地图渲染，避免污染全局作用域。
(function () {
    // 功能说明：转义文本，防止拼接 HTML 时被特殊字符破坏页面结构。
    function escapeHtml(value) {
        // 先把值转成字符串，空值兜底为空串，再依次替换 5 个 HTML 敏感字符。
        return String(value || '')
            .replace(/&/g, '&amp;')      // & 转 &amp;（必须最先替换）
            .replace(/</g, '&lt;')       // < 转 &lt;
            .replace(/>/g, '&gt;')       // > 转 &gt;
            .replace(/"/g, '&quot;')     // 双引号转 &quot;
            .replace(/'/g, '&#039;');    // 单引号转 &#039;
    }

    // 功能说明：过滤出经纬度有效的站点，无坐标的点无法在地图上标出。
    function getValidStops(stops) {
        // stops 为空时用空数组兜底，逐项保留经纬度转数字后为真值的站点。
        return (stops || []).filter((item) => {
            // 经纬度转数字后为真值才保留（0 或缺失视为无效）。
            return Number(item.longitude) && Number(item.latitude);
        });
    }

    // 功能说明：根据站点数组在高德地图上创建地图、打编号标记、按序连线并自适应视野。
    function renderPlannerRouteMap(stops) {
        // 取得地图容器 DOM 节点。
        const mapElement = document.getElementById('planner-map');
        // 过滤出坐标有效的站点列表。
        const validStops = getValidStops(stops);

        // 地图容器、AMap 脚本或有效站点任一缺失都直接返回，避免报错。
        if (!mapElement || !window.AMap || !validStops.length) {
            return;
        }

        // 清空容器内的占位内容。
        mapElement.innerHTML = '';
        // 创建高德地图实例：缩放 11 级，中心点取第一个站点经纬度，2D 视图。
        const map = new AMap.Map('planner-map', {
            zoom: 11,                                                              // 初始缩放级别
            center: [Number(validStops[0].longitude), Number(validStops[0].latitude)],  // 以首个站点为中心
            viewMode: '2D'                                                         // 平面视图模式
        });

        const markerList = [];   // 收集所有标记，供最后 setFitView 使用
        const path = [];         // 按游览顺序收集连线点

        // 遍历每个有效站点，依次创建标记、信息窗并加入地图。
        validStops.forEach((stop, index) => {
            // 组装该站点的 [经度, 纬度] 坐标数组。
            const position = [Number(stop.longitude), Number(stop.latitude)];
            // 把坐标推入连线路径数组，保持与游览顺序一致。
            path.push(position);

            // 创建标记点；编号来自数组下标（index+1），即后端排好的游览顺序，而非高德计算。
            const marker = new AMap.Marker({
                position: position,          // 标记所在坐标
                title: stop.name,            // 鼠标悬停提示文字
                label: {
                    direction: 'top',        // 标签显示在标记上方
                    content: `<div class="map-marker-label-cartoon">${index + 1}</div>`  // 圆圈序号内容
                }
            });

            // 有图片则生成 img 标签，否则空串；src 与 alt 均做转义。
            const imageHtml = stop.image
                ? `<img class="map-info-image-cartoon" src="${escapeHtml(stop.image)}" alt="${escapeHtml(stop.name)}">`
                : '';
            // 创建点击标记后弹出的信息窗：图片 + 名称 + 介绍，向上偏移 30px。
            const infoWindow = new AMap.InfoWindow({
                offset: new AMap.Pixel(0, -30),   // 相对标记的像素偏移
                content: `<div class="map-info-cartoon">${imageHtml}<strong>${escapeHtml(stop.name)}</strong><p>${escapeHtml(stop.intro)}</p></div>`
            });

            // 绑定点击事件：点击标记时在该标记位置打开信息窗。
            marker.on('click', function () {
                infoWindow.open(map, marker.getPosition());
            });

            marker.setMap(map);            // 把标记添加到地图
            markerList.push(marker);       // 收集标记，供自适应视野使用
        });

        // 两个及以上站点才需要连线；用 Polyline 按 path 顺序首尾相连成示意路线（非道路导航）。
        if (path.length > 1) {
            const polyline = new AMap.Polyline({
                path: path,                 // 连线点序列
                strokeColor: '#0f766e',     // 线条颜色
                strokeWidth: 6,             // 线宽
                strokeOpacity: 0.9,         // 透明度
                lineJoin: 'round'           // 拐角圆角
            });
            polyline.setMap(map);           // 把折线添加到地图
        }

        // 自动缩放平移，让所有标记点落入可视范围并四周各留 50px 边距。
        map.setFitView(markerList, false, [50, 50, 50, 50]);
    }

    // 功能说明：页面初次加载时读取 route-stop-data 数据岛并渲染已有路线（同步/详情页场景）。
    function renderInitialRouteMap() {
        // 取得存放站点 JSON 的数据岛节点。
        const dataElement = document.getElementById('route-stop-data');

        // 数据岛不存在（如空表单页）直接返回。
        if (!dataElement) {
            return;
        }

        // 数据岛内容是后端 json_script 输出的 JSON，解析后交给渲染函数。
        const stops = JSON.parse(dataElement.textContent || '[]');
        renderPlannerRouteMap(stops);
    }

    // 暴露给 planner_stream.js：流式模式下收到 route_stops/done 事件后调用它重绘地图。
    window.renderPlannerRouteMap = renderPlannerRouteMap;
    // 立即执行一次初始渲染，处理页面已带数据的场景。
    renderInitialRouteMap();
})();
