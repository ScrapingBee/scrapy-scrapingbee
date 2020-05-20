from setuptools import setup

setup(
    name='scrapy-scrapingbee',
    version='0.0.2',
    url='https://github.com/scrapingbee/scrapy-scrapingbee',
    description='JavaScript support and proxy rotation for Scrapy with ScrapingBee',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Ari Bajo Rouvinen',
    maintainer='Pierre de Wulf',
    maintainer_email='hello@scrapingbee.com',
    license='MIT',
    packages=['scrapy_scrapingbee'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Scrapy',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.5',
    install_requires=['scrapy'],
)
