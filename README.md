# Point of Sale (POS) System

## Description
This project is a Point of Sale (POS) system designed to optimize retail operations. Featuring a user-friendly shopping cart interface and robust reporting capabilities, it allows for efficient transaction processing, inventory tracking, and supplier monitoring. Ideal for small and medium-sized retail businesses.

## Features
- User-friendly shopping cart interface
- Robust reporting capabilities
- Inventory tracking
- Supplier monitoring
- Sales reports generation
- PDF and Excel report exports

## Prerequisites
- Python 3.x
- Pipenv
  
## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/username/pos-system.git
    ```
2. Navigate to the project directory:
    ```bash
    cd pos-system
    ```
3. Install the dependencies && 3rds parties:
    ```bash
    pip install pipenv
    pipenv install Django
    pipenv install openxl
    pipenv install html2pdf
    ```

## Usage

## Usage
1. Activate the virtual environment:
    ```bash
    pipenv shell
    ```
2. Apply migrations:
    ```bash
    pipenv run python manage.py makemigrations
    pipenv run python manage.py migrate
    ```
3. Run the application:
    ```bash
    pipenv run python manage.py runserver
    ```
4. Open your web browser and go to:
    ```
    http://localhost:8000
    ```


For questions or collaboration, please contact me via [Twitter](https://twitter.com/Wa_ViGo) or email at [your.email@example.com](mailto:geralnede@gmail.com).

## License
This project is licensed under the MIT License.

