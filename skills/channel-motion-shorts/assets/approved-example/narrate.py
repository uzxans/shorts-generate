import asyncio,json,subprocess
from pathlib import Path
import edge_tts
p=Path(__file__).resolve().parent
lines=[
(0,4,'Один запрос — и сервер под угрозой?'),
(4,10,'Серверные компоненты Реакт готовят интерфейс на сервере. Браузер получает результат, а клиентские компоненты добавляют интерактивность.'),
(14,10,'В декабре двадцать пятого года обнаружили критическую уязвимость. В уязвимых версиях специально созданный запрос мог запустить код на сервере без входа в аккаунт.'),
(24,10,'Например, магазин на Некст с Эпп Роутером. Витрина работает, но внутри может оставаться уязвимый пакет. Работает — не значит защищено.'),
(34,12,'Проверь версии фреймворка и серверных пакетов Реакт. Установи актуальные исправления для поддерживаемой ветки. Затем выполни тесты, пересобери приложение и разверни его заново.'),
(46,8,'Главное: патч должен дойти до сервера. Актуальные инструкции ищи в официальной документации Реакт.'),
(54,4,'Подпишись, чтобы не пропустить новые разборы.')]
async def main():
 for i,(start,duration,text) in enumerate(lines):
  f=p/'public'/f'voice-{i+1}.mp3'
  if not f.exists():await edge_tts.Communicate(text,'ru-RU-DmitryNeural',rate='+5%').save(str(f))
  length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(f)]))
  print(i+1,length,'slot',duration,flush=True)
 (p/'narration.json').write_text(json.dumps(lines,ensure_ascii=False,indent=2))
asyncio.run(main())
