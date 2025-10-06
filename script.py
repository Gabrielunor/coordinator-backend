#!/usr/bin/env python3
# Copyright (c) 2025 Gabriel Cavalcante. Todos os direitos reservados.
# Este software é proprietário e só pode ser utilizado mediante autorização expressa do autor.

import math
import argparse
from hilbertcurve.hilbertcurve import HilbertCurve
from pyproj import CRS, Transformer

# --- Configurações do Sistema de Referência de Coordenadas (SIRGAS 2000 / Brazil Albers) ---
# Marco zero (Easting at false origin, Northing at false origin) conforme WKT fornecido:
MARCO_ZERO_X = 5000000
MARCO_ZERO_Y = 10000000

# Área de cobertura fornecida pelo usuário:
Y_MAX_AREA = 12300000
Y_MIN_AREA = 6300000
X_MAX_AREA = 7330000
X_MIN_AREA = 2290000

# WKT do sistema de coordenadas SIRGAS 2000 / Brazil Albers fornecido pelo usuário
SIRGAS_2000_BRAZIL_ALBERS_WKT = '''
PROJCRS["SIRGAS 2000 / Brazil Albers",
    BASEGEOGCRS["SIRGAS 2000",
        DATUM["Sistema de Referencia Geocentrico para las AmericaS 2000",
            ELLIPSOID["GRS 1980",6378137,298.257222101,
                LENGTHUNIT["metre",1]]],
        PRIMEM["Greenwich",0,
            ANGLEUNIT["degree",0.0174532925199433]],
        ID["EPSG",4674]],
    CONVERSION["Brazil Albers",
        METHOD["Albers Equal Area",
            ID["EPSG",9822]],
        PARAMETER["Latitude of false origin",-12,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8821]],
        PARAMETER["Longitude of false origin",-54,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8822]],
        PARAMETER["Latitude of 1st standard parallel",-2,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8823]],
        PARAMETER["Latitude of 2nd standard parallel",-22,
            ANGLEUNIT["degree",0.0174532925199433],
            ID["EPSG",8824]],
        PARAMETER["Easting at false origin",5000000,
            LENGTHUNIT["metre",1],
            ID["EPSG",8826]],
        PARAMETER["Northing at false origin",10000000,
            LENGTHUNIT["metre",1],
            ID["EPSG",8827]]],
    CS[Cartesian,2],
        AXIS["(E)",east,
            ORDER[1],
            LENGTHUNIT["metre",1]],
        AXIS["(N)",north,
            ORDER[2],
            LENGTHUNIT["metre",1]],
    USAGE[
        SCOPE["Statistical analysis."],
        AREA["Brazil - onshore."],
        BBOX[-33.78,-74.01,5.28,-34.74]],
    ID["EPSG",10857]]
'''

# Definir os sistemas de coordenadas para pyproj
crs_wgs84 = CRS("EPSG:4326")  # WGS84 (latitude, longitude)
crs_sirgas_albers = CRS(SIRGAS_2000_BRAZIL_ALBERS_WKT)

# Criar o transformador global
transformer = Transformer.from_crs(crs_wgs84, crs_sirgas_albers, always_xy=True)

def convert_wgs84_to_sirgas_albers(lon, lat):
    """
    Converte coordenadas WGS84 (longitude, latitude) para SIRGAS 2000 / Brazil Albers (Easting, Northing).
    
    Args:
        lon (float): Longitude em WGS84.
        lat (float): Latitude em WGS84.
        
    Returns:
        tuple: Uma tupla (easting, northing) no sistema SIRGAS 2000 / Brazil Albers.
    """
    easting, northing = transformer.transform(lon, lat)
    return easting, northing


# --- Funções de utilidade ---

def to_base36(number):
    """
    Converte um número inteiro para sua representação em Base36.
    """
    if not isinstance(number, int) or number < 0:
        raise ValueError("O número deve ser um inteiro não negativo.")

    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    base = len(alphabet)
    
    if number == 0:
        return alphabet[0]

    base36_chars = []
    while number > 0:
        remainder = number % base
        base36_chars.append(alphabet[remainder])
        number //= base
    
    return "".join(reversed(base36_chars))


# --- Definição dos níveis de resolução e seus tamanhos em metros ---
# Nível 0: 100km = 100000m
# A cada nível, o tamanho do tile é dividido por 2.
# O nível máximo (menor tile) será 1m.

def get_tile_size_from_level(level):
    base_size = 100000.0  # 100 km em metros
    if level < 0:
        raise ValueError("O nível não pode ser negativo.")
    
    tile_size = base_size / (2**level)
    
    # Garantir que o tamanho mínimo do tile seja 1m
    if tile_size < 1.0:
        return 1.0
    
    return tile_size


def generate_tiles(level):
    tile_size = get_tile_size_from_level(level)
    print(f"Gerando tiles para o nível {level} com tamanho de {tile_size} metros.")

    # Ajustar a origem do grid de tiles para que o marco zero esteja no centro de um tile.
    # O canto inferior esquerdo do tile que contém o marco zero como seu centro seria:
    # (MARCO_ZERO_X - tile_size / 2, MARCO_ZERO_Y - tile_size / 2)
    
    # Calcular o índice do tile que contém X_MIN_AREA e Y_MIN_AREA, considerando o marco zero como centro do tile (0,0)
    min_tile_x_idx = math.floor((X_MIN_AREA - (MARCO_ZERO_X - tile_size / 2)) / tile_size)
    min_tile_y_idx = math.floor((Y_MIN_AREA - (MARCO_ZERO_Y - tile_size / 2)) / tile_size)

    # Calcular o índice do tile que contém X_MAX_AREA e Y_MAX_AREA
    max_tile_x_idx = math.ceil((X_MAX_AREA - (MARCO_ZERO_X - tile_size / 2)) / tile_size) - 1
    max_tile_y_idx = math.ceil((Y_MAX_AREA - (MARCO_ZERO_Y - tile_size / 2)) / tile_size) - 1

    num_tiles_x = max_tile_x_idx - min_tile_x_idx + 1
    num_tiles_y = max_tile_y_idx - min_tile_y_idx + 1

    print(f"Número de tiles na largura: {num_tiles_x} (de {min_tile_x_idx} a {max_tile_x_idx})")
    print(f"Número de tiles na altura: {num_tiles_y} (de {min_tile_y_idx} a {max_tile_y_idx})")

    tiles = []
    
    # Para a curva de Hilbert, precisamos de um grid quadrado e o parâmetro 'p' (ordem da curva).
    # O 'p' deve ser tal que 2^p seja maior ou igual à maior dimensão do grid (max(num_tiles_x, num_tiles_y)).
    max_dim = max(num_tiles_x, num_tiles_y)
    p = math.ceil(math.log2(max_dim)) if max_dim > 0 else 1 # p deve ser pelo menos 1
    
    if p == 0: p = 1

    hilbert_curve = HilbertCurve(p, 2) # 2 dimensões

    for j_idx in range(min_tile_y_idx, max_tile_y_idx + 1):
        for i_idx in range(min_tile_x_idx, max_tile_x_idx + 1):
            # Coordenadas do canto inferior esquerdo do tile
            tile_x_min = (MARCO_ZERO_X - tile_size / 2) + i_idx * tile_size
            tile_y_min = (MARCO_ZERO_Y - tile_size / 2) + j_idx * tile_size
            
            # Coordenadas do canto superior direito do tile
            tile_x_max = tile_x_min + tile_size
            tile_y_max = tile_y_min + tile_size

            # Normalizar as coordenadas do tile para a curva de Hilbert
            # O tile (min_tile_x_idx, min_tile_y_idx) será mapeado para (0,0) na curva de Hilbert.
            normalized_i = i_idx - min_tile_x_idx
            normalized_j = j_idx - min_tile_y_idx

            # Calcular a distância de Hilbert para o centro do tile normalizado
            hilbert_distance = hilbert_curve.distances_from_points([[normalized_i, normalized_j]])[0]
            
            # Codificar a distância de Hilbert em Base36
            hilbert_id_base36 = to_base36(hilbert_distance)

            tiles.append({
                'id': hilbert_id_base36,
                'level': level,
                'size': tile_size,
                'bbox': (tile_x_min, tile_y_min, tile_x_max, tile_y_max),
                'grid_coords': (i_idx, j_idx), # Coordenadas no grid relativo ao marco zero
                'normalized_grid_coords': (normalized_i, normalized_j), # Coordenadas normalizadas para Hilbert
                'hilbert_distance': hilbert_distance
            })
    
    # Ordenar os tiles pela distância de Hilbert (já estão ordenados implicitamente pela geração da curva)
    # Mas para garantir, podemos manter a ordenação explícita.
    tiles.sort(key=lambda t: t['hilbert_distance'])
            
    return tiles


def get_tile_id_from_coordinates(easting, northing, target_level):
    """
    Encontra o ID do tile (em Base36) para uma dada coordenada SIRGAS 2000 / Brazil Albers
    em um nível de resolução específico.
    """
    tile_size = get_tile_size_from_level(target_level)

    # Calcular o índice do tile que contém a coordenada (easting, northing)
    # em relação à origem do grid que tem o marco zero no centro do tile (0,0).
    
    # Coordenadas do canto inferior esquerdo do tile central (que contém o marco zero)
    origin_x_central_tile = MARCO_ZERO_X - tile_size / 2
    origin_y_central_tile = MARCO_ZERO_Y - tile_size / 2

    # Calcular o índice do tile (i_idx, j_idx) para a coordenada fornecida
    i_idx = math.floor((easting - origin_x_central_tile) / tile_size)
    j_idx = math.floor((northing - origin_y_central_tile) / tile_size)

    # Para a curva de Hilbert, precisamos do grid normalizado.
    # Primeiro, precisamos saber o min_tile_x_idx e min_tile_y_idx para o nível alvo
    # para calcular o offset de normalização.
    
    # Recalcular min_tile_x_idx e min_tile_y_idx para o target_level
    min_tile_x_idx_for_level = math.floor((X_MIN_AREA - (MARCO_ZERO_X - tile_size / 2)) / tile_size)
    min_tile_y_idx_for_level = math.floor((Y_MIN_AREA - (MARCO_ZERO_Y - tile_size / 2)) / tile_size)

    normalized_i = i_idx - min_tile_x_idx_for_level
    normalized_j = j_idx - min_tile_y_idx_for_level

    # Calcular a ordem 'p' da curva de Hilbert para o grid completo da área de interesse
    # no nível de resolução alvo.
    width_area = X_MAX_AREA - X_MIN_AREA
    height_area = Y_MAX_AREA - Y_MIN_AREA

    num_tiles_x_total = math.ceil(width_area / tile_size)
    num_tiles_y_total = math.ceil(height_area / tile_size)

    max_dim = max(num_tiles_x_total, num_tiles_y_total)
    p = math.ceil(math.log2(max_dim)) if max_dim > 0 else 1
    if p == 0: p = 1

    hilbert_curve = HilbertCurve(p, 2)

    # Calcular a distância de Hilbert para as coordenadas normalizadas
    hilbert_distance = hilbert_curve.distances_from_points([[normalized_i, normalized_j]])[0]
    
    # Codificar a distância de Hilbert em Base36
    hilbert_id_base36 = to_base36(hilbert_distance)

    return hilbert_id_base36


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera tiles para uma área específica usando um sistema de coordenadas com marco zero central e os ordena por curva de Hilbert.")
    parser.add_argument('--level', type=int, default=0, help='O nível de resolução para a geração dos tiles (0 para 100km, aumentando para tiles menores).')
    parser.add_argument('--find_id_lon', type=float, help='Longitude WGS84 para encontrar o ID do tile.')
    parser.add_argument('--find_id_lat', type=float, help='Latitude WGS84 para encontrar o ID do tile.')

    args = parser.parse_args()

    if args.find_id_lon is not None and args.find_id_lat is not None:
        # Converter WGS84 para SIRGAS 2000 / Brazil Albers
        easting, northing = convert_wgs84_to_sirgas_albers(args.find_id_lon, args.find_id_lat)
        print(f"Coordenadas WGS84 ({args.find_id_lon}, {args.find_id_lat}) convertidas para SIRGAS Albers: ({easting}, {northing})")

        # Encontrar o ID do tile para as coordenadas convertidas
        target_level_for_id = args.level # Usar o nível especificado para encontrar o ID
        tile_id = get_tile_id_from_coordinates(easting, northing, target_level_for_id)
        print(f"O ID do tile para as coordenadas ({easting}, {northing}) no nível {target_level_for_id} é: {tile_id}")
    else:
        # Caso contrário, gerar e listar os tiles
        try:
            tiles = generate_tiles(args.level)
            print(f"Total de tiles gerados para o nível {args.level}: {len(tiles)}")
            if tiles:
                print("Primeiro tile gerado (ordenado por Hilbert):")
                print(tiles[0])
                print("Último tile gerado (ordenado por Hilbert):")
                print(tiles[-1])

                # Verificar se o marco zero está contido em algum tile
                found_marco_zero_tile = False
                for tile in tiles:
                    x_min, y_min, x_max, y_max = tile['bbox']
                    if x_min <= MARCO_ZERO_X < x_max and y_min <= MARCO_ZERO_Y < y_max:
                        print(f"Marco zero ({MARCO_ZERO_X}, {MARCO_ZERO_Y}) está contido no tile: {tile['id']} com bbox {tile['bbox']}")
                        found_marco_zero_tile = True
                        break
                if not found_marco_zero_tile:
                    print("Atenção: Marco zero não encontrado em nenhum tile gerado. Verifique a lógica de cobertura.")

        except ValueError as e:
            print(f"Erro: {e}")