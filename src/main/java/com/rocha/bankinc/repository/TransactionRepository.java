package com.rocha.bankinc.repository;

import com.rocha.bankinc.entity.Transaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;


@Repository
public interface TransactionRepository extends JpaRepository<Transaction, Long> {

    Transaction findByCardIdAndTransactionId(String cardId, Long transactionId);
}

