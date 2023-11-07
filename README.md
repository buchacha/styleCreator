# Style creator bot
Стильный помощник - бот, позволяющий примерить одежду по вашей фотографии и параметрам одежды и предлагающий подобранные варианты в магазине.

Для распознавания одежды на картинках используется API https://serpapi.com/google-lens-api

# Необходимые для запуска технологии
Ниже приведены ссылки с описанием процесса установки на ОС Ubuntu.

## Mongo
https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/

## Redis
https://redis.io/docs/getting-started/installation/install-redis-on-linux/

## Дополнительно
### Пакетный менеджер
При разработке использовалась система управления пакетами Miniconda. Для дальнейшего запуска также рекомендуется использовать какой-нибудь пакетный менеджер. Установка:
```
mkdir -p ~/opt/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/opt/miniconda3/miniconda.sh
bash ~/opt/miniconda3/miniconda.sh -b -u -p ~/opt/miniconda3
rm -rf ~/opt/miniconda3/miniconda.sh
~/opt/miniconda3/bin/conda init bash
~/opt/miniconda3/bin/conda init zsh
```

После установки Miniconda необходимо создать окружение 
```
conda update conda
conda create -n env python=3.11
conda activate env
```
и установить в окружение необходимые пакеты:

### Requirements
```
pip install -r requirements.txt
```

> **Внимание**
> Репозиторий нейронной сети должен находиться в репозитории бота 

### Config
В корневом каталоге проекта следует создать файл **config.py** со следующими переменными:

- **token**: в неё помещается токен бота, через которого будет производиться взаимодействие. Токен можно получить в Telegram в диалоге с BotFather по кнопке API Token для вашего бота.

- **mongo_client**  = "mongodb://localhost:27017/"

- **db_name** = "style-creator-bot-DB"

- **redis_url** =  "redis://@localhost:6379/0"

- **api_token**: токен распознающей системы google lens

- **id_to_send**: список ids администраторов, выдающих pro-версию

Redis и Mongo запускаются под своими стандартными портами (см. документацию).

### Запуск
В папке проекта введите в терминале
```
python main.py
```
