def leave_policy():
    return """
        Annual Leave : 14
        Casual Leave : 7
        Medical Leave : 10
        Total Leave : 31
        
        If you are the agent calling this function to add an employee, include the leave balance as 31. Not a dictionary with all types of leaves. 
        """

def company_policy():
    return """
        Employees must work 8 hours per day.
        Remote work allowed twice per week.
        """