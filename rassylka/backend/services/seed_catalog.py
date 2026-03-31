"""
Seed data for car brands, models, and part categories.
Run: python -m backend.services.seed_catalog
"""
import asyncio
import logging
from backend.database import async_session, init_db
from backend.models import CarBrand, CarModel, PartCategory
from sqlalchemy import select

logger = logging.getLogger("bidroute.seed_catalog")

# ═══════════════════════════════════════════════════
#  33 бренда + популярные модели
# ═══════════════════════════════════════════════════

BRANDS_AND_MODELS = {
    "Lada": {
        "name_ru": "Лада",
        "models": [
            ("Vesta", "Веста", True),
            ("Granta", "Гранта", True),
            ("Largus", "Ларгус", True),
            ("Niva", "Нива", True),
            ("XRAY", "Иксрей", False),
            ("Priora", "Приора", False),
            ("Kalina", "Калина", False),
            ("2107", "2107", False),
            ("2114", "2114", False),
            ("2110", "2110", False),
        ],
    },
    "Toyota": {
        "name_ru": "Тойота",
        "models": [
            ("Camry", "Камри", True),
            ("Corolla", "Королла", True),
            ("RAV4", "РАВ4", True),
            ("Land Cruiser", "Ленд Крузер", True),
            ("Land Cruiser Prado", "Прадо", True),
            ("Hilux", "Хайлюкс", False),
            ("Highlander", "Хайлендер", False),
            ("Yaris", "Ярис", False),
            ("Avensis", "Авенсис", False),
            ("Fortuner", "Фортунер", False),
        ],
    },
    "Hyundai": {
        "name_ru": "Хёндай",
        "models": [
            ("Solaris", "Солярис", True),
            ("Creta", "Крета", True),
            ("Tucson", "Туссон", True),
            ("Santa Fe", "Санта Фе", True),
            ("Elantra", "Элантра", False),
            ("ix35", "ix35", False),
            ("Accent", "Акцент", False),
            ("Sonata", "Соната", False),
            ("i30", "i30", False),
            ("Getz", "Гетц", False),
        ],
    },
    "Kia": {
        "name_ru": "Киа",
        "models": [
            ("Rio", "Рио", True),
            ("Ceed", "Сид", True),
            ("Sportage", "Спортейдж", True),
            ("Sorento", "Соренто", True),
            ("Optima", "Оптима", False),
            ("Cerato", "Церато", False),
            ("Soul", "Соул", False),
            ("Picanto", "Пиканто", False),
            ("K5", "К5", False),
            ("Seltos", "Селтос", True),
        ],
    },
    "BMW": {
        "name_ru": "БМВ",
        "models": [
            ("3 Series", "3 Серия", True),
            ("5 Series", "5 Серия", True),
            ("X3", "X3", True),
            ("X5", "X5", True),
            ("X1", "X1", False),
            ("1 Series", "1 Серия", False),
            ("7 Series", "7 Серия", False),
            ("X6", "X6", False),
            ("X7", "X7", False),
            ("4 Series", "4 Серия", False),
        ],
    },
    "Mercedes-Benz": {
        "name_ru": "Мерседес",
        "models": [
            ("C-Class", "С-Класс", True),
            ("E-Class", "Е-Класс", True),
            ("GLC", "GLC", True),
            ("GLE", "GLE", True),
            ("S-Class", "С-Класс", False),
            ("A-Class", "А-Класс", False),
            ("GLA", "GLA", False),
            ("GLB", "GLB", False),
            ("CLA", "CLA", False),
            ("Sprinter", "Спринтер", False),
        ],
    },
    "Volkswagen": {
        "name_ru": "Фольксваген",
        "models": [
            ("Polo", "Поло", True),
            ("Tiguan", "Тигуан", True),
            ("Passat", "Пассат", True),
            ("Golf", "Гольф", True),
            ("Touareg", "Туарег", False),
            ("Jetta", "Джетта", False),
            ("Touran", "Туран", False),
            ("Caddy", "Кэдди", False),
            ("Multivan", "Мультивен", False),
            ("Amarok", "Амарок", False),
        ],
    },
    "Nissan": {
        "name_ru": "Ниссан",
        "models": [
            ("Qashqai", "Кашкай", True),
            ("X-Trail", "Х-Трейл", True),
            ("Almera", "Альмера", True),
            ("Juke", "Жук", False),
            ("Teana", "Теана", False),
            ("Pathfinder", "Патфайндер", False),
            ("Murano", "Мурано", False),
            ("Note", "Ноте", False),
            ("Tiida", "Тиида", False),
            ("Navara", "Навара", False),
        ],
    },
    "Ford": {
        "name_ru": "Форд",
        "models": [
            ("Focus", "Фокус", True),
            ("Mondeo", "Мондео", True),
            ("Kuga", "Куга", True),
            ("Fiesta", "Фиеста", False),
            ("Explorer", "Эксплорер", False),
            ("EcoSport", "ЭкоСпорт", False),
            ("Transit", "Транзит", False),
            ("Ranger", "Рейнджер", False),
            ("Maverick", "Маверик", False),
            ("S-MAX", "С-МАКС", False),
        ],
    },
    "Renault": {
        "name_ru": "Рено",
        "models": [
            ("Duster", "Дастер", True),
            ("Logan", "Логан", True),
            ("Sandero", "Сандеро", True),
            ("Kaptur", "Каптюр", True),
            ("Megane", "Меган", False),
            ("Fluence", "Флюенс", False),
            ("Koleos", "Колеос", False),
            ("Arkana", "Аркана", False),
            ("Scenic", "Сценик", False),
            ("Kangoo", "Кангу", False),
        ],
    },
    "Mazda": {
        "name_ru": "Мазда",
        "models": [
            ("CX-5", "CX-5", True),
            ("3", "3", True),
            ("6", "6", True),
            ("CX-9", "CX-9", False),
            ("CX-3", "CX-3", False),
            ("CX-7", "CX-7", False),
            ("MX-5", "MX-5", False),
            ("5", "5", False),
        ],
    },
    "Honda": {
        "name_ru": "Хонда",
        "models": [
            ("CR-V", "СР-В", True),
            ("Civic", "Цивик", True),
            ("Accord", "Аккорд", True),
            ("HR-V", "HR-V", False),
            ("Jazz", "Джаз", False),
            ("Pilot", "Пилот", False),
            ("Fit", "Фит", False),
            ("Odyssey", "Одиссей", False),
        ],
    },
    "Mitsubishi": {
        "name_ru": "Мицубиси",
        "models": [
            ("Outlander", "Аутлендер", True),
            ("Lancer", "Лансер", True),
            ("ASX", "ASX", True),
            ("Pajero", "Паджеро", True),
            ("L200", "L200", False),
            ("Eclipse Cross", "Эклипс Кросс", False),
            ("Pajero Sport", "Паджеро Спорт", False),
            ("Galant", "Галант", False),
        ],
    },
    "Chevrolet": {
        "name_ru": "Шевроле",
        "models": [
            ("Cruze", "Круз", True),
            ("Niva", "Нива", True),
            ("Aveo", "Авео", True),
            ("Lacetti", "Лачетти", False),
            ("Captiva", "Каптива", False),
            ("Orlando", "Орландо", False),
            ("Cobalt", "Кобальт", False),
            ("Tahoe", "Тахо", False),
        ],
    },
    "Skoda": {
        "name_ru": "Шкода",
        "models": [
            ("Octavia", "Октавия", True),
            ("Rapid", "Рапид", True),
            ("Kodiaq", "Кодиак", True),
            ("Superb", "Суперб", False),
            ("Fabia", "Фабия", False),
            ("Karoq", "Карок", False),
            ("Yeti", "Йети", False),
            ("Kamiq", "Камик", False),
        ],
    },
    "Audi": {
        "name_ru": "Ауди",
        "models": [
            ("A4", "A4", True),
            ("A6", "A6", True),
            ("Q5", "Q5", True),
            ("Q7", "Q7", True),
            ("A3", "A3", False),
            ("Q3", "Q3", False),
            ("A5", "A5", False),
            ("A8", "A8", False),
            ("Q8", "Q8", False),
            ("TT", "TT", False),
        ],
    },
    "Subaru": {
        "name_ru": "Субару",
        "models": [
            ("Forester", "Форестер", True),
            ("Outback", "Аутбек", True),
            ("XV", "XV", True),
            ("Impreza", "Импреза", False),
            ("Legacy", "Легаси", False),
            ("WRX", "WRX", False),
        ],
    },
    "Volvo": {
        "name_ru": "Вольво",
        "models": [
            ("XC60", "XC60", True),
            ("XC90", "XC90", True),
            ("S60", "S60", False),
            ("V60", "V60", False),
            ("XC40", "XC40", False),
            ("S90", "S90", False),
        ],
    },
    "Lexus": {
        "name_ru": "Лексус",
        "models": [
            ("RX", "RX", True),
            ("NX", "NX", True),
            ("LX", "LX", True),
            ("IS", "IS", False),
            ("ES", "ES", False),
            ("GX", "GX", False),
            ("UX", "UX", False),
        ],
    },
    "Infiniti": {
        "name_ru": "Инфинити",
        "models": [
            ("QX50", "QX50", True),
            ("QX60", "QX60", True),
            ("Q50", "Q50", False),
            ("FX", "FX", False),
            ("QX70", "QX70", False),
            ("QX80", "QX80", False),
        ],
    },
    "Land Rover": {
        "name_ru": "Ленд Ровер",
        "models": [
            ("Range Rover", "Рейндж Ровер", True),
            ("Range Rover Sport", "Рейндж Ровер Спорт", True),
            ("Discovery", "Дискавери", True),
            ("Freelander", "Фрилендер", False),
            ("Evoque", "Эвок", False),
            ("Defender", "Дефендер", False),
        ],
    },
    "Porsche": {
        "name_ru": "Порше",
        "models": [
            ("Cayenne", "Кайен", True),
            ("Macan", "Макан", True),
            ("Panamera", "Панамера", False),
            ("911", "911", False),
            ("Taycan", "Тайкан", False),
        ],
    },
    "Jeep": {
        "name_ru": "Джип",
        "models": [
            ("Grand Cherokee", "Гранд Чероки", True),
            ("Wrangler", "Рэнглер", True),
            ("Compass", "Компас", False),
            ("Renegade", "Ренегат", False),
            ("Cherokee", "Чероки", False),
        ],
    },
    "Peugeot": {
        "name_ru": "Пежо",
        "models": [
            ("308", "308", True),
            ("3008", "3008", True),
            ("408", "408", False),
            ("208", "208", False),
            ("5008", "5008", False),
            ("Partner", "Партнёр", False),
        ],
    },
    "Suzuki": {
        "name_ru": "Сузуки",
        "models": [
            ("Vitara", "Витара", True),
            ("SX4", "SX4", True),
            ("Grand Vitara", "Гранд Витара", True),
            ("Jimny", "Джимни", False),
            ("Swift", "Свифт", False),
        ],
    },
    "Chery": {
        "name_ru": "Чери",
        "models": [
            ("Tiggo 7 Pro", "Тигго 7 Про", True),
            ("Tiggo 4", "Тигго 4", True),
            ("Tiggo 8 Pro", "Тигго 8 Про", True),
            ("Arrizo 8", "Арризо 8", False),
            ("Tiggo 4 Pro", "Тигго 4 Про", False),
        ],
    },
    "Haval": {
        "name_ru": "Хавейл",
        "models": [
            ("Jolion", "Джолион", True),
            ("F7", "F7", True),
            ("Dargo", "Дарго", True),
            ("H9", "H9", False),
            ("F7x", "F7x", False),
            ("M6", "M6", False),
        ],
    },
    "Geely": {
        "name_ru": "Джили",
        "models": [
            ("Coolray", "Кулрей", True),
            ("Atlas Pro", "Атлас Про", True),
            ("Monjaro", "Монджаро", True),
            ("Tugella", "Тугелла", False),
            ("Emgrand", "Эмгранд", False),
        ],
    },
    "Changan": {
        "name_ru": "Чанган",
        "models": [
            ("CS75 Plus", "CS75 Плюс", True),
            ("CS55 Plus", "CS55 Плюс", True),
            ("CS35 Plus", "CS35 Плюс", True),
            ("UNI-V", "UNI-V", False),
            ("UNI-K", "UNI-K", False),
        ],
    },
    "Zeekr": {
        "name_ru": "Зикр",
        "models": [
            ("001", "001", True),
            ("009", "009", False),
            ("X", "X", False),
        ],
    },
    "Daihatsu": {
        "name_ru": "Дайхатсу",
        "models": [
            ("Terios", "Териос", True),
            ("Sirion", "Сирион", False),
            ("YRV", "YRV", False),
        ],
    },
    "Alpina": {
        "name_ru": "Альпина",
        "models": [
            ("B3", "B3", True),
            ("B4", "B4", False),
            ("XD3", "XD3", False),
        ],
    },
    "УАЗ": {
        "name_ru": "УАЗ",
        "models": [
            ("Патриот", "Патриот", True),
            ("Хантер", "Хантер", True),
            ("Буханка", "Буханка", True),
            ("Профи", "Профи", False),
        ],
    },
}

# ═══════════════════════════════════════════════════
#  40 категорий запчастей → 8 кластеров
# ═══════════════════════════════════════════════════

PART_CATEGORIES = [
    # Кластер: тормоза
    ("тормозные колодки", "Тормозные колодки", "тормоза"),
    ("тормозные диски", "Тормозные диски", "тормоза"),
    ("суппорт тормозной", "Суппорт тормозной", "тормоза"),
    ("тормозные шланги", "Тормозные шланги", "тормоза"),

    # Кластер: подвеска
    ("амортизаторы", "Амортизаторы", "подвеска"),
    ("стойки стабилизатора", "Стойки стабилизатора", "подвеска"),
    ("рычаг подвески", "Рычаг подвески", "подвеска"),
    ("рулевая рейка", "Рулевая рейка", "подвеска"),
    ("рулевой наконечник", "Рулевой наконечник", "подвеска"),
    ("шаровая опора", "Шаровая опора", "подвеска"),
    ("сайлентблок", "Сайлентблок", "подвеска"),

    # Кластер: привод
    ("ШРУС", "ШРУС", "привод"),
    ("пыльник ШРУСа", "Пыльник ШРУСа", "привод"),
    ("сцепление", "Сцепление", "привод"),
    ("карданный вал", "Карданный вал", "привод"),
    ("ступица", "Ступица", "привод"),
    ("подшипник ступицы", "Подшипник ступицы", "привод"),

    # Кластер: двигатель
    ("ремень ГРМ", "Ремень ГРМ", "двигатель"),
    ("помпа", "Помпа", "двигатель"),
    ("термостат", "Термостат", "двигатель"),
    ("радиатор", "Радиатор", "двигатель"),
    ("прокладка ГБЦ", "Прокладка ГБЦ", "двигатель"),

    # Кластер: фильтры
    ("масляный фильтр", "Масляный фильтр", "фильтры"),
    ("воздушный фильтр", "Воздушный фильтр", "фильтры"),
    ("салонный фильтр", "Салонный фильтр", "фильтры"),
    ("топливный фильтр", "Топливный фильтр", "фильтры"),
    ("свечи зажигания", "Свечи зажигания", "фильтры"),

    # Кластер: электрика
    ("генератор", "Генератор", "электрика"),
    ("стартер", "Стартер", "электрика"),
    ("катушка зажигания", "Катушка зажигания", "электрика"),
    ("аккумулятор", "Аккумулятор", "электрика"),
    ("датчик ABS", "Датчик ABS", "электрика"),
    ("датчик кислорода", "Датчик кислорода", "электрика"),

    # Кластер: кузов
    ("фара", "Фара", "кузов"),
    ("зеркало", "Зеркало", "кузов"),
    ("бампер", "Бампер", "кузов"),
    ("крыло", "Крыло", "кузов"),
    ("лобовое стекло", "Лобовое стекло", "кузов"),

    # Кластер: выхлоп
    ("глушитель", "Глушитель", "выхлоп"),
    ("выхлопная труба", "Выхлопная труба", "выхлоп"),
    ("катализатор", "Катализатор", "выхлоп"),
    ("клапан EGR", "Клапан EGR", "выхлоп"),
]


async def seed_catalog():
    """Seed brands, models, and part categories into DB."""
    await init_db()

    async with async_session() as db:
        # Check if already seeded
        existing = (await db.execute(select(CarBrand))).scalars().all()
        if existing:
            logger.info(f"Catalog already seeded ({len(existing)} brands). Skipping.")
            return {"brands": len(existing), "status": "already_seeded"}

        brand_count = 0
        model_count = 0

        for brand_name, data in BRANDS_AND_MODELS.items():
            brand = CarBrand(
                name=brand_name,
                name_ru=data["name_ru"],
                active=True,
            )
            db.add(brand)
            await db.flush()  # get brand.id
            brand_count += 1

            for model_name, model_ru, popular in data["models"]:
                model = CarModel(
                    brand_id=brand.id,
                    name=model_name,
                    name_ru=model_ru,
                    popular=popular,
                    active=True,
                )
                db.add(model)
                model_count += 1

        # Part categories
        part_count = 0
        for name, name_ru, cluster in PART_CATEGORIES:
            cat = PartCategory(name=name, name_ru=name_ru, cluster=cluster, active=True)
            db.add(cat)
            part_count += 1

        await db.commit()
        logger.info(f"Seeded: {brand_count} brands, {model_count} models, {part_count} part categories")
        return {"brands": brand_count, "models": model_count, "parts": part_count}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_catalog())
