def prepare_ccam_upload_transactions(prisoner_list):
    # Save excel file for upload to JIFMS
    payments = []
    for key, p in prisoner_list.items():
        if p.overpayment:
            for case in p.cases_list:
                if case.transaction:
                    payments.append({'prisoner': p, 'case': case})
            payments.append({'prisoner': p})
        else:
            for case in p.cases_list:
                if case.transaction:
                    payments.append({'prisoner': p, 'case': case})
    return payments