# Инструкция по диагностике и устранению неисправностей

## 1. Управление скоростью вращения корпусных вентиляторов (Supermicro, IPMI)
### Применение
- Снижение шума.
- Контроль перегрева после изменения настроек.

### Инструкция
1. Подключите патчкорд к LAN-разъему IPMI.
2. Настройте IP в BIOS: Advanced → IPMI Configuration (DHCP или Static IP).
3. Войдите в Web-интерфейс IPMI через браузер.
4. Авторизуйтесь (логин/пароль: ADMIN).
5. Перейдите в Fan Mode → Set Fan to Optimal Speed → Save.

## 2. Настройка RAID-массива (LSI/Avago)
### Инструкция
1. Войдите в BIOS (DEL) и переключитесь в Advanced mode.
2. Перейдите: Settings → IO-Ports → LSI MegaRAID Configuration Utility.
3. Создайте массив RAID 5:
   - Очистите конфигурацию.
   - Выберите диски и примените изменения.
   - Включите Drive Cache (Enabled) и Default Initialization (Fast).
4. Проверьте состояние массива (Virtual Drive Management).
5. Инициализируйте массив через Gparted (Linux) или Управление дисками (Windows).

## 3. Восстановление ОС через систему восстановления (IPDROM/Clonezilla)
### Важно
- Все данные на системном диске будут удалены.

### Инструкция
1. Войдите в BIOS (DEL/F2) и выберите загрузку с USB (UEFI Transcend Partition 1 / Sandisk Clonezilla).
2. В оболочке восстановления:
   - Выберите язык и клавиатурную раскладку.
   - Найдите средство восстановления.
   - Укажите системный диск.
3. Подтвердите восстановление (Y) и дождитесь завершения процесса.
4. Перезагрузите сервер.

## 4. Сбор логов для анализа (RAID-контроллер и сервера Supermicro)
### RAID-контроллер (LSI/AVAGO)
1. Запустите MegaRAID Storage Manager.
2. Сохраните логи через Save TTY Log.
3. Отправьте файл с указанием серийного номера сервера.

### Сервера Supermicro
1. Используйте Supermicro Doctor.
2. Авторизуйтесь (логин/пароль: ADMIN).
3. Сгенерируйте отчеты (System Information, Event Log) и отправьте их на email.

## 5. Диагностика звуковых сигналов
### RAID-контроллер
- Проверьте состояние массива через MegaRAID Storage Manager.
- Отключите сигнал (Silence Alarm).
- Восстановите диск (Change to Unconfigured Good → Import Foreign Configuration).

### Материнская плата
- Сравните сигналы с таблицей ошибок (см. документацию).

## 6. Проблемы с видеоизображением (IPMI, сервер, видеокарты)
### Черный экран в IPMI
- По умолчанию IPMI работает только через аналоговый порт VGA (Aspeed Graphics).
- Если используются две видеокарты, выберите активную через перемычку JPG1.

### Пропало изображение
1. Проверьте кабели и монитор.
2. Попробуйте сменить видеокарту через перемычку JPG1:
   - 1-2: Aspeed Graphics (IPMI, VGA).
   - 2-3: Дискретная видеокарта / встроенная в ЦП (HDMI, DVI, DP).

## 7. Ошибки и сбои RAID-массива
### Отмонтировался RAID-массив
1. Проверьте, что массив видится в ОС и смонтирован.
2. Установите MegaCLI:
   ```bash
   echo 'deb http://hwraid.le-vert.net/debian stretch main' | sudo tee -a /etc/apt/sources.list
   sudo wget -O - https://hwraid.le-vert.net/debian/hwraid.le-vert.net.gpg.key | apt-key add -
   sudo apt update
   sudo apt-get install megacli
   ```
3. Проверьте состояние массива:
   ```bash
   MegaCli -LDInfo -Lall -aALL
   ```

### После замены дисков странный звук
- Проверьте, не вышел ли диск из строя.
- Верните диск в массив, если возможно.

## 8. Сервер не загружается / синий экран
### Диагностика
1. Проверьте настройки гибернации в BIOS.
2. Протестируйте оперативную память.
3. Проверьте диск (smartctl):
   ```bash
   sudo apt install smartmontools
   sudo smartctl -a /dev/sda
   ```
4. Восстановите заводской образ ОС.

## 9. Проблемы с сетевым подключением (LAN)
1. В Ubuntu создайте новый профиль сетевого подключения.
2. Проверьте настройки IP и шлюза.
3. Перезагрузите сервер.

## 10. Камеры и архив
### Потеря связи с камерами
1. Проверьте диски на битые сектора:
   ```bash
   sudo badblocks -sv /dev/sda
   ```
2. Подробнее: [losst.pro](https://losst.pro/proverka-diska-na-bitye-sektory-v-linux).

### Проблемы с записью архива
1. Проверьте скорость ввода/вывода RAID-массива (Crystal Disk Mark).
2. Отключите Firewall и антивирус на время теста.
3. Проверьте режим работы RAID (Write Back / Write Through).

## 11. Прочие проблемы
### Не включается регистратор
1. Проверьте RAID-массив.
2. Проверьте блок питания.

### Проблемы с программой Axxon
1. Проверьте логи и состояние SSD.
2. Если проблема в Axxon, переустановите ПО.

### Не определяется плата сухих контактов
1. Проверьте подключение к материнской плате.
2. Установите драйверы из ПО Интеллект.

---



