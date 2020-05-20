from setuptools import setup

setup(
    name='scrapy-scrapingbee',
    version='0.0.1',
    url='https://github.com/scrapingbee/scrapy-scrapingbee',
    description='JavaScript support and proxy rotation for Scrapy with ScrapingBee',
    author='Ari Bajo Rouvinen',
    maintainer='Pierre de Wulf',
    maintainer_email='hello@scrapingbee.com',
    license='MIT',
    packages=['scrapy_scrapingbee'],
    python_requires='>=3.5',
    install_requires=['scrapy'],
)
