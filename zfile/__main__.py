
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        'zfile.fapi:app',
        host='127.0.0.1',
        port=4000,
        reload=True,
        log_config="logging_config.yaml"
    )
