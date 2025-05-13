import pandas as pd
import time
import json
from typing import Dict, Any, List, Tuple

# Константы, как в app.py
MAX_ALERT_HISTORY_SIZE = 100

# --- Функции, адаптированные из app.py --- 

def format_telegram_message_sim(row: pd.Series) -> str:
    """Упрощенная функция форматирования сообщения для симуляции."""
    # В реальном приложении здесь telegram_service.format_telegram_message
    return f"Alert for TxID: {row.get('TxID_sim')}, Amount: {row.get('Amount_sim')}"

def send_telegram_alert_sim(bot_token: str, chat_id: str, message_html: str) -> bool:
    """Симуляция отправки алерта."""
    # print(f"    [SIM_SEND] To: {chat_id}, Msg: {message_html}") # Раскомментировать для детального лога отправки
    return True # Всегда успешно для симуляции

def save_alert_history_sim(history: Dict[str, Dict[str, Any]], current_cycle: int, limit_query_input_sim: int) -> Dict[str, Dict[str, Any]]:
    """Сохраняет историю алертов, применяя ротацию (адаптировано)."""
    
    max_history_size = limit_query_input_sim
    
    if len(history) > max_history_size:
        # print(f"    [Cycle {current_cycle} SAVE_HISTORY] History size {len(history)} > {max_history_size}. Rotating...")
        
        # Модифицированная сортировка: сначала не-success, потом success; внутри каждой группы по времени
        sorted_hashes = sorted(
            history.keys(), 
            key=lambda k: (
                1 if history[k].get('status') == 'success' else 0, # Статус success "тяжелее"
                history[k].get('last_attempt_time', 0) # Затем по времени
            )
        )
        
        num_to_remove = len(history) - max_history_size
        hashes_to_remove = sorted_hashes[:num_to_remove]
        # print(f"        [Cycle {current_cycle} SAVE_HISTORY] Candidates for removal (sorted by preference): {hashes_to_remove}")
        for h_to_remove in hashes_to_remove:
            # print(f"        [Cycle {current_cycle} SAVE_HISTORY] Removing by rotation: {h_to_remove} (Status: {history.get(h_to_remove, {}).get('status')}, LastAttemptTime: {history.get(h_to_remove, {}).get('last_attempt_time')})")
            if h_to_remove in history:
                 del history[h_to_remove]
            else:
                print(f"        [Cycle {current_cycle} SAVE_HISTORY] WARNING: Hash {h_to_remove} not found during rotation.")
    
    return history

def process_telegram_alerts_sim(
    transactions_df: pd.DataFrame, 
    current_alert_history: Dict[str, Dict[str, Any]], 
    bot_token: str, 
    chat_id: str,
    current_cycle: int
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """Обрабатывает отправку Telegram алертов (адаптировано)."""
    
    history_updated = False
    current_time_sim = time.time() # Используем реальное время для last_attempt_time

    if 'TxID_sim' not in transactions_df.columns:
        print(f"[Cycle {current_cycle} PROCESS_ALERTS] CRITICAL: 'TxID_sim' not in DataFrame columns.")
        return current_alert_history, False

    # НЕ разворачиваем DataFrame, как в откаченной версии app.py
    for index, row in transactions_df.iterrows():
        tx_hash = row.get('TxID_sim')
        
        if not tx_hash or pd.isna(tx_hash):
            continue
            
        tx_hash_str = str(tx_hash)
        alert_info = current_alert_history.get(tx_hash_str)
        
        should_send = False
        is_retry = False
        current_attempt = 0
        
        if alert_info is None:
            should_send = True
            current_attempt = 1
            reason_for_sending = "new_transaction"
        elif alert_info.get('status') in ["pending", "error"]:
            last_attempt_time = alert_info.get('last_attempt_time', 0)
            attempts_done = alert_info.get('attempt', 0) 
            if attempts_done < 5 and (current_time_sim - last_attempt_time >= 10): # Уменьшенный интервал для ретраев в симуляции
                should_send = True
                is_retry = True
                current_attempt = attempts_done + 1
                reason_for_sending = "retry_pending_or_error"
            # else:
                # print(f"    [Cycle {current_cycle} PROCESS_ALERTS] TxID: {tx_hash_str}, Status: {alert_info.get('status')}, Attempts: {attempts_done}, TimeDiff: {current_time_sim - last_attempt_time:.2f}s. No retry needed.")
                
        if should_send:
            print(f"[Cycle {current_cycle} PROCESS_ALERTS] ALERT WOULD BE SENT for TxID: {tx_hash_str} (Amount: {row.get('Amount_sim')}, Reason: {reason_for_sending}, Attempt: {current_attempt}) History Status Before: {alert_info.get('status') if alert_info else 'None'}")
            message_html = format_telegram_message_sim(row)
            if message_html:
                # В реальном коде здесь вызов send_telegram_alert
                success = send_telegram_alert_sim(bot_token, chat_id, message_html) 
                
                new_status = "success" if success else ("error" if current_attempt >= 5 else "pending")
                sent_time_sim = current_time_sim if success else (alert_info.get('sent_time') if alert_info and 'sent_time' in alert_info else None) 
                
                current_alert_history[tx_hash_str] = {
                    'status': new_status,
                    'attempt': current_attempt,
                    'last_attempt_time': current_time_sim,
                    'sent_time': sent_time_sim
                }
                history_updated = True
                # print(f"    [Cycle {current_cycle} PROCESS_ALERTS] Updated history for {tx_hash_str}: Status {new_status}, Attempt {current_attempt}")
                time.sleep(0.01) # Небольшая задержка между "отправками"
            else:
                print(f"[Cycle {current_cycle} PROCESS_ALERTS] FAILED TO FORMAT message for TxID: {tx_hash_str}")
    
    return current_alert_history, history_updated

# --- Основная логика симуляции ---

def run_simulation():
    print("--- Starting Alert Simulation v2 ---")

    # 1. Параметры симуляции
    num_cycles = 50               # Количество циклов обновления
    limit_query_input_sim = 5     # Максимальный размер истории (для теста ротации)
    num_transactions_in_df = 7    # Количество транзакций, которые "видит" fetch на каждом цикле
                                  # Должно быть > limit_query_input_sim для проверки ротации
    
    bot_token_sim = "test_token"
    chat_id_sim = "test_chat_id"

    # 2. Создаем "персистентную" историю (имитация LocalStorage)
    #    В реальном app.py она загружается из LocalStorage через load_alert_history()
    persistent_alert_history: Dict[str, Dict[str, Any]] = {}

    # 3. Создаем фиксированный DataFrame (имитация fetch_transactions)
    #    Транзакции идут от "старых" к "новым" по TxID_sim
    transactions_data = []
    for i in range(num_transactions_in_df):
        transactions_data.append({
            'TxID_sim': f"tx_hash_{i:03d}", 
            'Amount_sim': 1000 + i * 100, 
            'OtherData': f"data_{i}"
            # Добавьте другие поля, если format_telegram_message_sim их использует
        })
    fixed_df = pd.DataFrame(transactions_data)
    print(f"Simulation will use a fixed DataFrame with {len(fixed_df)} transactions:")
    print(fixed_df.head(10).to_string())
    print(f"History limit (limit_query_input_sim): {limit_query_input_sim}")
    print(f"Total simulation cycles: {num_cycles}\n")

    # 4. Основной цикл симуляции
    for cycle in range(1, num_cycles + 1):
        print(f"--- Cycle {cycle}/{num_cycles} ---")
        
        # В реальном app.py: alert_history = load_alert_history()
        # Здесь мы используем наш persistent_alert_history, который обновляется между циклами
        current_history_for_processing = persistent_alert_history.copy() # Копируем перед передачей в process
        # print(f"  [Cycle {cycle}] Loaded history (size {len(current_history_for_processing)}): {list(current_history_for_processing.keys())}")

        # В реальном app.py: df = fetch_transactions(...)
        # Здесь мы используем наш fixed_df
        
        # Обработка алертов
        updated_history, was_history_updated_in_cycle = process_telegram_alerts_sim(
            fixed_df, 
            current_history_for_processing, # Передаем копию
            bot_token_sim, 
            chat_id_sim,
            cycle
        )
        
        if was_history_updated_in_cycle:
            # print(f"  [Cycle {cycle}] History was updated in process_telegram_alerts_sim.")
            # В реальном app.py: save_alert_history(updated_history)
            # Здесь мы вызываем нашу симуляцию сохранения, которая применяет ротацию
            final_history_after_save = save_alert_history_sim(updated_history, cycle, limit_query_input_sim)
            persistent_alert_history = final_history_after_save # Обновляем "персистентное" состояние
            # print(f"  [Cycle {cycle}] Persistent history updated (size {len(persistent_alert_history)}): {list(persistent_alert_history.keys())}")
        else:
            # print(f"  [Cycle {cycle}] History was NOT updated in process_telegram_alerts_sim.")
            # Если история не менялась, нет смысла ее "сохранять" (и применять ротацию)
            # persistent_alert_history остается прежним
            pass
            
        print(f"  [Cycle {cycle}] End of cycle. Current persistent history (size {len(persistent_alert_history)}):")
        # Печатаем статусы для наглядности
        for tx_id_hist, data_hist in sorted(persistent_alert_history.items()):
            print(f"    TxID: {tx_id_hist}, Status: {data_hist.get('status')}, Attempt: {data_hist.get('attempt')}, LastAttempt: {time.strftime('%H:%M:%S', time.localtime(data_hist.get('last_attempt_time',0)))}")
        
        if cycle < num_cycles:
            # print(f"  Simulating time delay before next cycle...\n")
            time.sleep(0.1) # Небольшая задержка между циклами

    print("--- Simulation Finished ---")
    final_tx_ids_in_history = sorted(list(persistent_alert_history.keys()))
    print(f"Final TxIDs in history (size {len(final_tx_ids_in_history)}): {final_tx_ids_in_history}")

if __name__ == "__main__":
    run_simulation() 