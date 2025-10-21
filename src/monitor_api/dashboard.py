"""HTML шаблон для дашборда мониторинга."""


def get_dashboard_html() -> str:
    """Получить HTML код дашборда.

    Returns:
        HTML строка с дашбордом
    """
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Avito Worker Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                             Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                color: #333;
                margin-bottom: 30px;
                text-align: center;
            }
            .cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .card h3 {
                color: #666;
                font-size: 14px;
                margin-bottom: 10px;
            }
            .card .value {
                font-size: 32px;
                font-weight: bold;
                color: #333;
            }
            .card.success .value {
                color: #4caf50;
            }
            .card.warning .value {
                color: #ff9800;
            }
            .card.error .value {
                color: #f44336;
            }
            .card.info .value {
                color: #2196f3;
            }
            .refresh-btn {
                display: block;
                width: 100%;
                padding: 15px;
                background: #2196f3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                margin-bottom: 20px;
            }
            .refresh-btn:hover {
                background: #1976d2;
            }
            .last-update {
                text-align: center;
                color: #666;
                font-size: 14px;
            }
            .error-box {
                background: #ffebee;
                border-left: 4px solid #f44336;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .error-box h4 {
                color: #c62828;
                margin-bottom: 5px;
            }
            .error-box p {
                color: #666;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Avito Worker Dashboard</h1>

            <button class="refresh-btn" onclick="loadStats()">
                🔄 Обновить статистику
            </button>

            <div id="error-container"></div>

            <div class="cards">
                <div class="card info">
                    <h3>Всего сообщений</h3>
                    <div class="value" id="total-messages">-</div>
                </div>
                <div class="card warning">
                    <h3>В очереди</h3>
                    <div class="value" id="pending-messages">-</div>
                </div>
                <div class="card info">
                    <h3>В обработке</h3>
                    <div class="value" id="processing-messages">-</div>
                </div>
                <div class="card success">
                    <h3>Обработано</h3>
                    <div class="value" id="completed-messages">-</div>
                </div>
                <div class="card error">
                    <h3>Ошибок</h3>
                    <div class="value" id="failed-messages">-</div>
                </div>
                <div class="card info">
                    <h3>Активных диалогов</h3>
                    <div class="value" id="active-dialogs">-</div>
                </div>
            </div>

            <div class="last-update">
                Последнее обновление: <span id="last-update">-</span>
            </div>
        </div>

        <script>
            async function loadStats() {
                try {
                    const response = await fetch('/stats');
                    const data = await response.json();

                    document.getElementById('total-messages').textContent =
                        data.total_messages || 0;
                    document.getElementById('pending-messages').textContent =
                        data.pending_messages || 0;
                    document.getElementById('processing-messages').textContent =
                        data.processing_messages || 0;
                    document.getElementById('completed-messages').textContent =
                        data.completed_messages || 0;
                    document.getElementById('failed-messages').textContent =
                        data.failed_messages || 0;
                    document.getElementById('active-dialogs').textContent =
                        data.active_dialogs || 0;

                    const now = new Date().toLocaleString('ru-RU');
                    document.getElementById('last-update').textContent = now;

                    const errorContainer = document.getElementById(
                        'error-container'
                    );
                    if (data.last_error) {
                        errorContainer.innerHTML = `
                            <div class="error-box">
                                <h4>⚠️ Последняя ошибка:</h4>
                                <p>${data.last_error}</p>
                            </div>
                        `;
                    } else {
                        errorContainer.innerHTML = '';
                    }
                } catch (error) {
                    console.error('Ошибка загрузки статистики:', error);
                    alert('Не удалось загрузить статистику');
                }
            }

            // Автоматическое обновление каждые 5 секунд
            setInterval(loadStats, 5000);

            // Загружаем при открытии страницы
            loadStats();
        </script>
    </body>
    </html>
    """
