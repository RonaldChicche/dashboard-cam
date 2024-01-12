import numpy as np
from scipy.stats import linregress


def detectar_outliers(lista, num_desviaciones=1):
    media = sum(lista) / len(lista)
    desviacion_estandar = (sum((x - media) ** 2 for x in lista) / len(lista)) ** 0.5
    outliers = [x for x in lista if abs(x - media) > num_desviaciones * desviacion_estandar]
    return outliers

def calcular_pendiente(lista_ajustada, list_index=None):
    # list of pos from cameras from config
    # lista_pos = [self.config['cameras'][i]['pos'] for i in list_index]

    x = np.arange(len(lista_ajustada))
    # x = np.array(lista_pos)
    y = np.array(lista_ajustada)
    print(f"x: {x}, y: {y}")
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    return slope

def ajustar_outliers(lista, compensacion, set_point, num_desviaciones=1):
    if len(lista) < 3:
        return [min([x + compensacion, x - compensacion, x], key=lambda y: abs(y - set_point)) for x in lista]

    outliers = detectar_outliers(lista, num_desviaciones)
    lista_sin_outliers = [x for x in lista if x not in outliers]
    mediana = np.median(lista_sin_outliers)

    # Ajustar outliers y elegir el valor más cercano a la mediana
    outliers_ajustados = []
    for outlier in outliers:
        ajuste_suma = outlier + compensacion
        ajuste_resta = outlier - compensacion
        ajuste_cercano = min([ajuste_suma, ajuste_resta, outlier], key=lambda x: abs(x - set_point))
        outliers_ajustados.append(ajuste_cercano)

    # Reemplazar outliers en la lista original
    lista_ajustada = lista.copy()
    for outlier, ajustado in zip(outliers, outliers_ajustados):
        idx = lista_ajustada.index(outlier)
        lista_ajustada[idx] = ajustado
    
    return lista_ajustada

if __name__ == "__main__":
    lista = [69, 420]
    lista_ajustada = ajustar_outliers(lista, 320, 70, num_desviaciones=1)
    print(lista_ajustada)
    pendiente = calcular_pendiente(lista_ajustada)
    print(pendiente)