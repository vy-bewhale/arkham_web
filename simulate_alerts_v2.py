import pandas as pd
import time
import json
from typing import Dict, Any, List, Tuple
import random # Для генерации случайного количества новых транзакций
import sys # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< НОВЫЙ ИМПОРТ

# Глобальный счетчик для уникальных TxID и "времени"
tx_id_counter = 0
current_sim_time = int(time.time()) # Начальное время для симуляции

# DataFrame для хранения ВСЕХ когда-либо сгенерированных транзакций
global_all_simulated_tx_df = pd.DataFrame(columns=['TxID_sim', 'Amount_sim', 'OtherData', 'SimTimestamp'])

def _generate_new_transactions(num_to_generate: int) -> pd.DataFrame:
    """Генерирует указанное количество новых, уникальных транзакций."""
    global tx_id_counter, current_sim_time, global_all_simulated_tx_df
    
    new_tx_list = []
    for _ in range(num_to_generate):
        tx_id = f"tx_hash_dyn_{tx_id_counter:04d}"
        amount = 1000 + random.randint(0, 10000)
        other_data = f"dynamic_data_{tx_id_counter}"
        sim_timestamp = current_sim_time
        
        new_tx_list.append({
            'TxID_sim': tx_id, 
            'Amount_sim': amount, 
            'OtherData': other_data,
            'SimTimestamp': sim_timestamp
        })
        tx_id_counter += 1
        current_sim_time += random.randint(1, 60) # Сдвигаем время для следующей транзакции
        
    new_tx_df = pd.DataFrame(new_tx_list)
    if not new_tx_df.empty:
        # Добавляем в глобальный пул
        global_all_simulated_tx_df = pd.concat([global_all_simulated_tx_df, new_tx_df], ignore_index=True)
        # Сортируем глобальный пул по времени (самые свежие вверху)
        global_all_simulated_tx_df = global_all_simulated_tx_df.sort_values(by='SimTimestamp', ascending=False).reset_index(drop=True)
        
    return new_tx_df

def simulate_arkham_api_call(limit: int) -> pd.DataFrame:
    """Имитирует вызов API, возвращая 'limit' самых свежих транзакций из глобального пула."""
    global global_all_simulated_tx_df
    if global_all_simulated_tx_df.empty:
        return pd.DataFrame(columns=['TxID_sim', 'Amount_sim', 'OtherData', 'SimTimestamp'])
    
    # Возвращаем срез самых свежих (уже отсортировано при добавлении)
    return global_all_simulated_tx_df.head(limit).copy()

# --- Функции, адаптированные из app.py (без изменений) --- 
def format_telegram_message_sim(row: pd.Series) -> str:
    """Упрощенная функция форматирования сообщения для симуляции."""
    return f"Alert for TxID: {row.get('TxID_sim')}, Amount: {row.get('Amount_sim')}, Time: {row.get('SimTimestamp')}"

def send_telegram_alert_sim(bot_token: str, chat_id: str, message_html: str) -> bool:
    """Симуляция отправки алерта."""
    return True

APP_MAX_ALERT_ATTEMPTS_SIM = 5 # Как в app.py

def _get_rotation_priority_key_sim(item_data: Dict[str, Any]):
    """Адаптированный ключ сортировки для ротации истории алертов."""
    status = item_data.get('status')
    attempt = item_data.get('attempt', 0)
    
    if status in ["error", "pending"]:
        if attempt >= APP_MAX_ALERT_ATTEMPTS_SIM:
            priority_group = 0 
        else:
            priority_group = 1 
        time_value = item_data.get('last_attempt_time', 0)
    elif status == "success":
        priority_group = 2 
        time_value = item_data.get('sent_time', 0) 
    else: 
        priority_group = 1 
        time_value = item_data.get('last_attempt_time', 0)
    return (priority_group, time_value)

def save_alert_history_sim(history: Dict[str, Dict[str, Any]], current_cycle: int, limit_query_input_sim: int) -> Dict[str, Dict[str, Any]]:
    """Сохраняет историю алертов, применяя ротацию (адаптировано для симуляции)."""
    max_history_size = 2 * limit_query_input_sim 
    history_copy = history.copy()
    
    if len(history_copy) > max_history_size:
        # print(f"    [Cycle {current_cycle} SAVE_HISTORY_SIM] History size {len(history_copy)} > {max_history_size}. Rotating...")
        sorted_keys_for_removal = sorted(
            history_copy.keys(), 
            key=lambda k: _get_rotation_priority_key_sim(history_copy[k])
        )
        num_to_remove = len(history_copy) - max_history_size
        hashes_to_remove = sorted_keys_for_removal[:num_to_remove]
        
        # print(f"    [Cycle {current_cycle} SAVE_HISTORY_SIM] Hashes to remove by rotation: {hashes_to_remove}")
        for h_key in hashes_to_remove:
            if h_key in history_copy:
                # details = history_copy.get(h_key, {})
                # print(f"        [SAVE_HISTORY_SIM] Removing: {h_key}, Priority: {_get_rotation_priority_key_sim(details)}")
                del history_copy[h_key]
    return history_copy

def process_telegram_alerts_sim(
    transactions_df_from_api: pd.DataFrame, 
    current_alert_history: Dict[str, Dict[str, Any]], 
    bot_token: str, 
    chat_id: str,
    current_cycle: int
) -> Tuple[Dict[str, Dict[str, Any]], bool]:
    """Обрабатывает отправку Telegram алертов (адаптировано)."""
    history_for_this_cycle = current_alert_history.copy() # Работаем с копией внутри функции
    history_updated_in_this_call = False
    current_time_for_attempts = time.time() 

    if 'TxID_sim' not in transactions_df_from_api.columns or transactions_df_from_api.empty:
        # print(f"[Cycle {current_cycle} PROCESS_ALERTS] No transactions from API or 'TxID_sim' missing.")
        return history_for_this_cycle, False

    # РАЗВОРАЧИВАЕМ DataFrame от API, чтобы обрабатывать от старых к новым
    # (API обычно возвращает от новых к старым)
    transactions_to_process = transactions_df_from_api.iloc[::-1]

    for index, row in transactions_to_process.iterrows():
        tx_hash = row.get('TxID_sim')
        if not tx_hash or pd.isna(tx_hash):
            continue
            
        tx_hash_str = str(tx_hash)
        alert_info = history_for_this_cycle.get(tx_hash_str)
        
        should_send = False
        is_retry = False
        current_attempt = 0
        reason_for_sending = ""
        
        if alert_info is None:
            should_send = True
            current_attempt = 1
            reason_for_sending = "new_transaction"
        elif alert_info.get('status') in ["pending", "error"]:
            last_attempt_time = alert_info.get('last_attempt_time', 0)
            attempts_done = alert_info.get('attempt', 0) 
            if attempts_done < APP_MAX_ALERT_ATTEMPTS_SIM and (current_time_for_attempts - last_attempt_time >= 10): # Интервал для ретраев
                should_send = True
                is_retry = True
                current_attempt = attempts_done + 1
                reason_for_sending = f"retry_{alert_info.get('status')}"
                
        if should_send:
            print(f"  [Cycle {current_cycle} ALERTS] SENDING for TxID: {tx_hash_str} (Amount: {row.get('Amount_sim')}, Time: {row.get('SimTimestamp')}, Reason: {reason_for_sending}, Attempt: {current_attempt}) History Status Before: {alert_info.get('status') if alert_info else 'None'}")
            message_html = format_telegram_message_sim(row)
            if message_html:
                success = send_telegram_alert_sim(bot_token, chat_id, message_html) 
                new_status = "success" if success else ("error" if current_attempt >= APP_MAX_ALERT_ATTEMPTS_SIM else "pending")
                sent_time_val = current_time_for_attempts if success else (alert_info.get('sent_time') if alert_info and 'sent_time' in alert_info else None) 
                
                history_for_this_cycle[tx_hash_str] = {
                    'status': new_status,
                    'attempt': current_attempt,
                    'last_attempt_time': current_time_for_attempts,
                    'sent_time': sent_time_val,
                    'original_SimTimestamp': row.get('SimTimestamp') # Сохраняем для отладки ротации
                }
                history_updated_in_this_call = True
                time.sleep(0.01) 
            else:
                print(f"  [Cycle {current_cycle} ALERTS] FAILED TO FORMAT message for TxID: {tx_hash_str}")
    
    return history_for_this_cycle, history_updated_in_this_call

# --- Основная логика симуляции ---
def run_simulation():
    global global_all_simulated_tx_df, tx_id_counter, current_sim_time
    global_all_simulated_tx_df = pd.DataFrame(columns=['TxID_sim', 'Amount_sim', 'OtherData', 'SimTimestamp']) # Сброс перед каждым запуском
    tx_id_counter = 0
    current_sim_time = int(time.time())

    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< НАЧАЛО БЛОКА ЛОГИРОВАНИЯ В ФАЙЛ
    original_stdout = sys.stdout
    log_file_name = "simulation_log.txt"

    print(f"Starting Dynamic Alert Simulation. Output will be logged to {log_file_name}") # Это выведется в консоль

    try:
        with open(log_file_name, 'w', encoding='utf-8') as f_log:
            sys.stdout = f_log # Перенаправляем stdout в файл
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< КОНЕЦ БЛОКА ЛОГИРОВАНИЯ В ФАЙЛ (начало try)

            print("--- Starting Dynamic Alert Simulation ---") # Это уже пойдет в файл

            # 1. Параметры симуляции
            NUM_CYCLES_SIM = 60
            LIMIT_QUERY_INPUT_SIM = 10
            NEW_TX_PER_CYCLE_MAX_SIM = 3
            
            bot_token_sim = "test_token"
            chat_id_sim = "test_chat_id"

            persistent_alert_history: Dict[str, Dict[str, Any]] = {}

            print(f"API window size (LIMIT_QUERY_INPUT_SIM): {LIMIT_QUERY_INPUT_SIM}")
            print(f"Max history size (2 * LIMIT_QUERY_INPUT_SIM): {2 * LIMIT_QUERY_INPUT_SIM}")
            print(f"Max new transactions per cycle: {NEW_TX_PER_CYCLE_MAX_SIM}")
            print(f"Total simulation cycles: {NUM_CYCLES_SIM}")

            # 2. Основной цикл симуляции
            for cycle in range(1, NUM_CYCLES_SIM + 1):
                print(f"--- Cycle {cycle}/{NUM_CYCLES_SIM} ---")
                
                # Генерируем новые транзакции и добавляем в глобальный пул
                num_new_to_generate = random.randint(0, NEW_TX_PER_CYCLE_MAX_SIM)
                _generate_new_transactions(num_new_to_generate)
                if num_new_to_generate > 0:
                    print(f"  Generated {num_new_to_generate} new transactions. Total in global pool: {len(global_all_simulated_tx_df)}")

                # Получаем "ответ от API" (скользящее окно)
                current_api_response_df = simulate_arkham_api_call(LIMIT_QUERY_INPUT_SIM)
                
                if not current_api_response_df.empty:
                    print(f"  API response for this cycle (oldest to newest after internal reversal):")
                    # Печатаем в порядке обработки (старые -> новые)
                    for _, r in current_api_response_df.iloc[::-1].iterrows():
                         print(f"    TxID: {r['TxID_sim']}, Time: {r['SimTimestamp']}")
                else:
                    print("  API response for this cycle is empty.")

                # Обработка алертов
                # process_telegram_alerts_sim ожидает, что persistent_alert_history - это история *до* этого цикла
                history_before_processing = persistent_alert_history.copy() 
                
                processed_history_for_cycle, was_history_updated_in_cycle = process_telegram_alerts_sim(
                    current_api_response_df, 
                    history_before_processing, 
                    bot_token_sim, 
                    chat_id_sim,
                    cycle
                )
                
                if was_history_updated_in_cycle:
                    # print(f"  [Cycle {cycle}] Alert history was updated by process_telegram_alerts_sim.")
                    # Сохраняем (с ротацией) обновленную историю в "персистентное" хранилище
                    persistent_alert_history = save_alert_history_sim(
                        processed_history_for_cycle, 
                        cycle, 
                        LIMIT_QUERY_INPUT_SIM
                    )
                else:
                    # Если process_telegram_alerts_sim не внесла изменений (например, нет новых транзакций и нет ретраев)
                    # то и не нужно вызывать save_alert_history_sim, так как ротация не нужна.
                    # persistent_alert_history остается таким, каким был.
                    # print(f"  [Cycle {cycle}] Alert history was NOT updated by process_telegram_alerts_sim.")
                    pass 
                
                print(f"  End of cycle. Persistent history size: {len(persistent_alert_history)}")
                # Для краткости не будем печатать всю историю каждый раз, если она большая
                if cycle % 10 == 0 or cycle == NUM_CYCLES_SIM : # Печатать детали каждые 10 циклов и в конце
                    print(f"  Detailed history for cycle {cycle} (oldest 'original_SimTimestamp' first):")
                    sorted_history_items = sorted(persistent_alert_history.items(), key=lambda item: item[1].get('original_SimTimestamp', 0))
                    for tx_id_hist, data_hist in sorted_history_items:
                        print(f"    TxID: {tx_id_hist}, Status: {data_hist.get('status')}, Attempt: {data_hist.get('attempt')}, OrigTime: {data_hist.get('original_SimTimestamp')}, LastAttempt: {time.strftime('%H:%M:%S', time.localtime(data_hist.get('last_attempt_time',0)))}")
                
                if cycle < NUM_CYCLES_SIM:
                    time.sleep(0.05) # Небольшая задержка

            print("\n--- Simulation Finished ---")
            print(f"Total unique transactions generated: {tx_id_counter}")
            print(f"Final persistent alert history size: {len(persistent_alert_history)}")
            
            # Проверим, есть ли "очень старые" транзакции в истории, которых уже давно нет в API окне
            if not global_all_simulated_tx_df.empty and persistent_alert_history:
                oldest_tx_in_api_window_time = global_all_simulated_tx_df.head(LIMIT_QUERY_INPUT_SIM)['SimTimestamp'].min()
                rotated_out_but_in_history = 0
                for tx_id, data in persistent_alert_history.items():
                    if data.get('original_SimTimestamp', float('inf')) < oldest_tx_in_api_window_time:
                        rotated_out_but_in_history +=1
                print(f"Transactions in history older than the current API window oldest: {rotated_out_but_in_history} (expected due to history size 2x API window)")

    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< НАЧАЛО БЛОКА ЛОГИРОВАНИЯ В ФАЙЛ (finally)
    finally:
        sys.stdout = original_stdout # Восстанавливаем stdout
        # Файл закроется автоматически благодаря 'with open'
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< КОНЕЦ БЛОКА ЛОГИРОВАНИЯ В ФАЙЛ

if __name__ == "__main__":
    run_simulation() 