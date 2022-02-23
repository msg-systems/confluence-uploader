"""
Delegates to the application module to start the program.

This is done so custom bootstrapping logic can be separated from the application.
"""
import cf_uploader.application as application

application.main()
