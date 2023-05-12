from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll
import datetime


class BotBase:

    def __init__(self, token_community, token_user, db=None):
        self._token_community = token_community
        self._token_user = token_user
        self._vk_community = vk_api.VkApi(token=self._token_community)
        self._vk_user = vk_api.VkApi(token=self._token_user)
        self._vk_user_api = self._vk_user.get_api()
        self._longpoll = VkLongPoll(self._vk_community)
        self._map_func = []
        self._map_message = []
        self.db = db

    def _map(self):
        return self._map_func, self._map_message

    def _map_add(self, func, message):
        self._map_func.append(func)
        self._map_message.append(message)

    def event(self, *args):
        def inner(func):
            self._map_add(func, args)
            return func
        return inner


class BotMethod(BotBase):

    def __init__(self, token_community, token_user, db=None):
        super().__init__(token_community, token_user, db)

    def send_message(self, user_id, message):
        self._vk_community.method('messages.send', {'user_id': user_id, 'message': message,
                                                    'random_id': randrange(10 ** 7)})

    def send_message_with_photo(self, user_id, message, photos):
        attachment = ""
        for photo in photos:
            attachment += "photo{}_{},".format(*photo)
        if len(attachment) > 0:
            attachment = attachment[:-1]
        self._vk_community.method('messages.send', {'user_id': user_id,
                                                    'access_token': self._token_user,
                                                    'message': message,
                                                    'attachment': attachment,
                                                    'random_id': 0})

    def get_data_user(self, user_id):
        user = self._vk_user_api.users.get(user_ids=user_id, fields="sex, bdate, city")
        if len(user) > 0:
            bdate = user[0].get("bdate")
            if bdate:
                date_list = bdate.split('.')
                if len(date_list) == 3:
                    date_today = datetime.date.today()
                    year = date_today.year - int(date_list[2])
                    month = date_today.month - int(date_list[1])
                    day = date_today.day - int(date_list[0])
                    if month <= 0:
                        if day < 0:
                            year -= 1
                    user[0]["bdate"] = year
                else:
                    user[0]["bdate"] = None
            return user[0]

    def get_city_id(self, city_name):
        cities_data = self._vk_user_api.database.getCities(country_id=1, q=city_name, need_all=0, count=1000)
        cities = cities_data['items']
        for city in cities:
            found_city_name = city.get('title')
            if found_city_name.lower() == city_name.lower():
                found_city_id = city.get('id')
                return int(found_city_id)

    def search_user(self, sex, age_from, age_to, city_id, offset):
        users = self._vk_user_api.users.search(sex=sex,
                                               age_from=age_from,
                                               age_to=age_to,
                                               city_id=city_id,
                                               fields="is_closed, id, first_name, last_name",
                                               status="1" or "6",
                                               count=50,
                                               offset=offset)
        if users.get("items"):
            list_1 = users['items']
            data = []
            for person_dict in list_1:
                if not person_dict.get('is_closed'):
                    first_name = person_dict.get('first_name')
                    last_name = person_dict.get('last_name')
                    vk_id = str(person_dict.get('id'))
                    vk_link = 'vk.com/id' + str(person_dict.get('id'))
                    data.append({"vk_id": vk_id, "vk_link": vk_link, "first_name": first_name, "last_name": last_name})
            return data

    def get_photo_comments_count(self, photo_id, user_id):
        try:
            comments = self._vk_user_api.photos.getComments(photo_id=photo_id, owner_id=user_id)
            if comments.get("count"):
                return comments.get("count")
            else:
                return 0
        except:
            return 0

    def get_photos_ids(self, user_id):
        photos_data = self._vk_user_api.photos.getAll(type="album", owner_id=user_id, extended=1, count=25)
        dict_photos = dict()
        list_1 = photos_data['items']
        for i in list_1:
            photo_id = str(i.get('id'))
            comments_count = self.get_photo_comments_count(photo_id, user_id)
            i_likes = i.get('likes')
            if i_likes.get('count'):
                rank = i_likes.get('count') + comments_count
                dict_photos[photo_id] = rank
        list_of_ids = sorted(dict_photos.items(), key=lambda item: item[1], reverse=True)
        return list_of_ids

    def search_couple_users(self, user_data):
        sex = 1 if user_data["sex"] == 2 else 2
        users = self.search_user(sex, user_data["age_from"], user_data["age_to"],
                                 self.get_city_id(user_data["city"]), user_data["offset_user"])
        return users

    def print_search_couple_user(self, user_id, search_data, photo_ids):
        photos = []
        for photo in photo_ids:
            photos.append((search_data["vk_id"], photo[0]))
        text = "👤 Имя: {}\n" \
               "👥 Фамилия: {}\n" \
               "🖥 Ссылка: {}\n\n" \
               "❗ Для следующего человека, введите: \"Вперёд\"".format(
                search_data["first_name"], search_data["last_name"], search_data["vk_link"])
        self.send_message_with_photo(user_id, text, photos)
