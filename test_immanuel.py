from immanuel import charts
from datetime import datetime

native = charts.Subject(
        date_time=datetime(2000, 1, 1, 10, 0, 0),
        latitude=32.71667,
        longitude=-117.15,
    )

natal = charts.Natal(native)

for object in natal.objects.values():
    print(object)

print("Teste do Immanuel concluído com sucesso!")
