"""多语维基文库种子书单。
为每种语言选取最核心的公版经典（5-20 部），作为该语种的基本盘。
与 pipeline/wikisource.py 配合使用——修改 API_URL 中的语言前缀即可切换。

已覆盖：en(英) fr(法) de(德) ja(日) ko(韩) ar(阿) es(西) ru(俄) la(拉丁) grc(古希腊)

格式：title, bu/domain, author, era
"""

SEEDS = {
    "en": [  # 英文维基文库 en.wikisource.org
        ("The Iliad", "Classics", "Homer", "8th century BC"),
        ("The Odyssey", "Classics", "Homer", "8th century BC"),
        ("The Republic", "Philosophy", "Plato", "4th century BC"),
        ("Nicomachean Ethics", "Philosophy", "Aristotle", "4th century BC"),
        ("Meditations", "Philosophy", "Marcus Aurelius", "2nd century"),
        ("Leviathan", "Political Philosophy", "Thomas Hobbes", "1651"),
        ("The Prince", "Political Philosophy", "Niccolò Machiavelli", "1532"),
        ("On the Origin of Species", "Science", "Charles Darwin", "1859"),
        ("The Wealth of Nations", "Economics", "Adam Smith", "1776"),
        ("Moby-Dick", "Novel", "Herman Melville", "1851"),
        ("Pride and Prejudice", "Novel", "Jane Austen", "1813"),
        ("Frankenstein", "Novel", "Mary Shelley", "1818"),
        ("The Divine Comedy", "Poetry", "Dante Alighieri", "1320"),
        ("The Federalist Papers", "Political Philosophy", "Hamilton, Madison, Jay", "1788"),
        ("Utopia", "Political Philosophy", "Thomas More", "1516"),
    ],
    "fr": [  # 法文维基文库 fr.wikisource.org
        ("Du contrat social", "Philosophy", "Jean-Jacques Rousseau", "1762"),
        ("Discours de la méthode", "Philosophy", "René Descartes", "1637"),
        ("Les Misérables", "Novel", "Victor Hugo", "1862"),
        ("Le Comte de Monte-Cristo", "Novel", "Alexandre Dumas", "1844"),
        ("Candide", "Novel", "Voltaire", "1759"),
        ("L'Étranger", "Novel", "Albert Camus", "1942"),
        ("À la recherche du temps perdu", "Novel", "Marcel Proust", "1913"),
        ("Les Fleurs du mal", "Poetry", "Charles Baudelaire", "1857"),
        ("De l'esprit des lois", "Political Philosophy", "Montesquieu", "1748"),
        ("Le Deuxième Sexe", "Philosophy", "Simone de Beauvoir", "1949"),
    ],
    "de": [  # 德文维基文库 de.wikisource.org
        ("Faust - Der Tragödie erster Teil", "Drama", "Johann Wolfgang von Goethe", "1808"),
        ("Also sprach Zarathustra", "Philosophy", "Friedrich Nietzsche", "1883"),
        ("Kritik der reinen Vernunft", "Philosophy", "Immanuel Kant", "1781"),
        ("Das Kapital", "Economics", "Karl Marx", "1867"),
        ("Die Verwandlung", "Novel", "Franz Kafka", "1915"),
        ("Der Prozess", "Novel", "Franz Kafka", "1925"),
        ("Buddenbrooks", "Novel", "Thomas Mann", "1901"),
        ("Die Welt als Wille und Vorstellung", "Philosophy", "Arthur Schopenhauer", "1819"),
        ("Über die ästhetische Erziehung des Menschen", "Philosophy", "Friedrich Schiller", "1795"),
        ("Siddhartha", "Novel", "Hermann Hesse", "1922"),
    ],
    "ja": [  # 日文维基文库 ja.wikisource.org
        ("源氏物語", "Literature", "紫式部", "11th century"),
        ("枕草子", "Literature", "清少納言", "1002"),
        ("方丈記", "Literature", "鴨長明", "1212"),
        ("徒然草", "Literature", "吉田兼好", "1331"),
        ("平家物語", "Literature", "佚名", "13th century"),
        ("学問のすゝめ", "Philosophy", "福沢諭吉", "1872"),
        ("こゝろ", "Novel", "夏目漱石", "1914"),
        ("羅生門", "Novel", "芥川龍之介", "1915"),
        ("雪国", "Novel", "川端康成", "1937"),
        ("草枕", "Novel", "夏目漱石", "1906"),
    ],
    "ko": [  # 韩文维基文库 ko.wikisource.org
        ("삼국사기", "History", "김부식", "1145"),
        ("삼국유사", "History", "일연", "1281"),
        ("훈민정음", "Linguistics", "세종대왕", "1446"),
        ("홍길동전", "Novel", "허균", "1612"),
        ("춘향전", "Novel", "佚名", "18th century"),
    ],
    "ar": [  # 阿拉伯文维基文库 ar.wikisource.org
        ("ألف ليلة وليلة", "Literature", "佚名", "9th century"),
        ("كليلة ودمنة", "Literature", "ابن المقفع", "8th century"),
        ("القرآن الكريم", "Religion", "—", "7th century"),
        ("مقدمة ابن خلدون", "History/Philosophy", "ابن خلدون", "1377"),
        ("المنقذ من الضلال", "Philosophy", "الغزالي", "12th century"),
    ],
    "es": [  # 西班牙文维基文库 es.wikisource.org
        ("Don Quijote de la Mancha", "Novel", "Miguel de Cervantes", "1605"),
        ("Cien años de soledad", "Novel", "Gabriel García Márquez", "1967"),
        ("El Aleph", "Short Stories", "Jorge Luis Borges", "1949"),
        ("Platero y yo", "Prose", "Juan Ramón Jiménez", "1914"),
        ("La vida es sueño", "Drama", "Pedro Calderón de la Barca", "1635"),
    ],
    "ru": [  # 俄文维基文库 ru.wikisource.org
        ("Война и мир", "Novel", "Лев Толстой", "1869"),
        ("Преступление и наказание", "Novel", "Фёдор Достоевский", "1866"),
        ("Анна Каренина", "Novel", "Лев Толстой", "1877"),
        ("Братья Карамазовы", "Novel", "Фёдор Достоевский", "1880"),
        ("Евгений Онегин", "Poetry", "Александр Пушкин", "1833"),
        ("Отцы и дети", "Novel", "Иван Тургенев", "1862"),
    ],
    "la": [  # 拉丁文维基文库 la.wikisource.org
        ("De Bello Gallico", "History", "Julius Caesar", "58 BC"),
        ("Aeneis", "Poetry", "Virgil", "19 BC"),
        ("Metamorphoses", "Poetry", "Ovid", "8 AD"),
        ("De Rerum Natura", "Philosophy", "Lucretius", "50 BC"),
        ("Confessiones", "Philosophy", "Augustine of Hippo", "400 AD"),
        ("Consolatio Philosophiae", "Philosophy", "Boethius", "524 AD"),
    ],
    "grc": [  # 古希腊文维基文库 el.wikisource.org (Ancient Greek)
        ("Ιλιάς", "Poetry", "Ὅμηρος", "8th century BC"),
        ("Ὀδύσσεια", "Poetry", "Ὅμηρος", "8th century BC"),
        ("Πολιτεία", "Philosophy", "Πλάτων", "4th century BC"),
        ("Ἠθικὰ Νικομάχεια", "Philosophy", "Ἀριστοτέλης", "4th century BC"),
        ("Συμπόσιον", "Philosophy", "Πλάτων", "4th century BC"),
        ("Ἀπολογία Σωκράτους", "Philosophy", "Πλάτων", "4th century BC"),
        ("Περὶ ποιητικῆς", "Aesthetics", "Ἀριστοτέλης", "4th century BC"),
    ],
}


def get_seeds(lang):
    """返回指定语言的种子书单 [(title, domain, author, era), ...]。"""
    if lang not in SEEDS:
        raise ValueError(f"不支持的语言: {lang}。支持: {', '.join(SEEDS.keys())}")
    return SEEDS[lang]


def seed_count():
    """统计各语种种子书数量。"""
    return {lang: len(items) for lang, items in SEEDS.items()}


if __name__ == "__main__":
    print("多语维基文库种子书单统计：")
    for lang, count in seed_count().items():
        print(f"  {lang}: {count} 部")
    print(f"  总计: {sum(seed_count().values())} 部 (覆盖 {len(SEEDS)} 语种)")
    print(f"\nISO 639 前缀对应的维基文库 URL：")
    for lang in SEEDS:
        print(f"  {lang}.wikisource.org → {lang}版")