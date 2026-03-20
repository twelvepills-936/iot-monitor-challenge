/**
 * IoT Monitor — Dashboard
 *
 * TODO: Реализовать дашборд мониторинга IoT-датчиков
 *
 * Требования:
 * - Таблица событий: время, sensor_id, location, temperature, humidity, severity, notification_sent
 * - Цвета строк: normal (зелёный), warning (жёлтый), critical (красный)
 * - Фильтры: по severity, по sensor_id, по диапазону дат
 * - Карточки сверху: всего событий, critical за сегодня, последнее событие
 * - Автообновление данных каждые 3 секунды (polling GET /api/events)
 * - Кнопка "Симулировать датчик" — форма для отправки тестового webhook POST /webhooks/sensor
 *
 * Можно использовать: Tailwind, MUI, или чистый CSS — на твой выбор
 */

function App() {
  return (
    <div>
      <h1>IoT Monitor</h1>
      <p>TODO: реализовать дашборд</p>
    </div>
  );
}

export default App;
